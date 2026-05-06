from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any
from unittest.mock import patch

from src.config import get_rag_settings
from src.product.models import ProductWorkflowResult
from src.product.presenters import build_document_review_view
from src.product.service import DEFAULT_WORKFLOW_QUERIES, _summarize_payload, index_loaded_documents
from src.providers.registry import build_provider_registry
from src.rag.loaders import load_document
from src.rag.service import normalize_rag_index
from src.storage.rag_store import load_rag_store
from src.structured.base import DocumentAgentPayload
from src.structured.envelope import TaskExecutionRequest
from src.structured.langgraph_workflow import run_structured_execution_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RISK_REVIEW_QUERY = (
    "List the contract risks, gaps, and red flags. "
    "Produce executive findings, blockers, business impact, and next actions grounded in the selected document."
)
DEFAULT_DOCUMENTS = [
    PROJECT_ROOT / "data" / "corpus_revisado" / "option_b_synthetic_premium" / "contracts" / "CTR-002_Master_Services_Agreement_Vendor_Draft.pdf",
    PROJECT_ROOT / "data" / "corpus_revisado" / "option_b_synthetic_premium" / "contracts" / "CTR-004_Data_Processing_Addendum.pdf",
    PROJECT_ROOT / "data" / "corpus_revisado" / "option_a_public_corpus_v2" / "contracts_and_procurement" / "common_paper_sla.md",
    PROJECT_ROOT / "data" / "corpus_revisado" / "option_a_public_corpus_v2" / "contracts_and_procurement" / "common_paper_dpa.md",
]


class _UploadAdapter:
    def __init__(self, path: Path) -> None:
        self.name = path.name
        self._content = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._content


def _token_set(value: str) -> set[str]:
    return {token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in (value or "")).split() if len(token) >= 4}


def _best_overlap(reference: str, candidates: list[str]) -> float:
    ref_tokens = _token_set(reference)
    if not ref_tokens:
        return 0.0
    best = 0.0
    for candidate in candidates:
        cand_tokens = _token_set(candidate)
        if not cand_tokens:
            continue
        overlap = len(ref_tokens & cand_tokens) / len(ref_tokens)
        if overlap > best:
            best = overlap
    return round(best, 4)


def _dedupe_score(findings: list[dict[str, Any]]) -> float:
    titles = [str(item.get("title") or "").strip().casefold() for item in findings if str(item.get("title") or "").strip()]
    if not titles:
        return 0.0
    unique_ratio = len(set(titles)) / len(titles)
    return round(unique_ratio, 4)


def _synthesis_success(metadata: dict[str, Any] | None) -> bool:
    return bool(isinstance(metadata, dict) and metadata.get("success") is True)


def _promotion_score(*, raw_score: float, config: dict[str, Any], metadata: dict[str, Any] | None) -> float:
    if not bool(config.get("synthesis_enabled")):
        return round(raw_score, 4)
    return round(raw_score, 4) if _synthesis_success(metadata) else 0.0


def _evaluate_view(result: ProductWorkflowResult, view: dict[str, Any]) -> dict[str, Any]:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    if not isinstance(payload, DocumentAgentPayload):
        raise RuntimeError("Document Review experiment expected a DocumentAgentPayload result.")

    structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
    extraction_payload = structured_response.get("extraction_payload") if isinstance(structured_response.get("extraction_payload"), dict) else {}
    risk_items = [item for item in extraction_payload.get("risks", []) if isinstance(item, dict)]
    action_items = [item for item in extraction_payload.get("action_items", []) if isinstance(item, dict)]
    missing_information = [str(item).strip() for item in extraction_payload.get("missing_information", []) if str(item).strip()]

    findings = [item for item in view.get("findings", []) if isinstance(item, dict)]
    finding_texts = [
        " ".join(
            str(item.get(field) or "")
            for field in ("title", "description", "recommendation", "snippet")
        )
        for item in findings
    ]
    next_step_texts = [str(item).strip() for item in view.get("next_steps", []) if str(item).strip()]
    watchout_texts = [str(item).strip() for item in view.get("watchouts", []) if str(item).strip()]

    risk_coverage = mean([
        _best_overlap(str(item.get("description") or ""), finding_texts) for item in risk_items
    ]) if risk_items else 1.0
    action_coverage = mean([
        _best_overlap(str(item.get("description") or ""), [*finding_texts, *next_step_texts]) for item in action_items
    ]) if action_items else 1.0
    gap_coverage = mean([
        _best_overlap(item, [*watchout_texts, *finding_texts, str(result.summary or "")]) for item in missing_information
    ]) if missing_information else 1.0

    grounded_findings = [
        item for item in findings
        if str(item.get("source") or "").strip() and str(item.get("chunkId") or "").strip() not in {"", "chunk_n/a"}
    ]
    grounding_ratio = round(len(grounded_findings) / len(findings), 4) if findings else 0.0
    decision_summary = view.get("decision_summary") if isinstance(view.get("decision_summary"), dict) else {}
    decision_score = 1.0 if all(str(decision_summary.get(key) or "").strip() for key in ("label", "status", "summary")) else 0.0

    top_blockers = [item for item in view.get("top_blockers", []) if isinstance(item, dict)]
    severe_titles = {
        str(item.get("title") or "").strip().casefold()
        for item in findings
        if str(item.get("severity") or "") in {"critical", "high"}
    }
    blocker_alignment = 0.0
    if top_blockers:
        aligned = 0
        for blocker in top_blockers:
            title = str(blocker.get("title") or "").strip().casefold()
            if title and title in severe_titles:
                aligned += 1
        blocker_alignment = round(aligned / len(top_blockers), 4)

    business_impact = [item for item in view.get("business_impact", []) if isinstance(item, dict)]
    business_impact_score = 1.0 if business_impact else 0.0

    total_score = round(
        (risk_coverage * 0.3)
        + (action_coverage * 0.15)
        + (gap_coverage * 0.1)
        + (grounding_ratio * 0.15)
        + (decision_score * 0.1)
        + (blocker_alignment * 0.1)
        + (_dedupe_score(findings) * 0.05)
        + (business_impact_score * 0.05),
        4,
    )

    return {
        "risk_coverage": round(risk_coverage, 4),
        "action_coverage": round(action_coverage, 4),
        "gap_coverage": round(gap_coverage, 4),
        "grounding_ratio": grounding_ratio,
        "decision_score": decision_score,
        "blocker_alignment": blocker_alignment,
        "dedupe_score": _dedupe_score(findings),
        "business_impact_score": business_impact_score,
        "finding_count": len(findings),
        "top_blocker_count": len(top_blockers),
        "total_score": total_score,
    }


def _build_result_from_structured(structured_result, *, workflow_id: str = "document_review") -> ProductWorkflowResult:
    summary, highlights, recommendation, warnings = _summarize_payload(
        workflow_id=workflow_id,
        structured_result=structured_result,
    )
    status = "completed" if structured_result.success else "error"
    if status == "completed" and warnings:
        status = "warning"
    return ProductWorkflowResult(
        workflow_id="document_review",
        workflow_label="Document Review",
        status=status,
        summary=summary,
        highlights=highlights,
        recommendation=recommendation,
        structured_result=structured_result,
        grounding_preview=None,
        artifacts=[],
        deck_export_kind=None,
        deck_available=False,
        warnings=warnings,
        debug_metadata={},
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _selected_documents() -> list[Path]:
    raw_paths = str(os.getenv("DOCUMENT_REVIEW_FINDINGS_EXPERIMENT_DOC_PATHS", "")).strip()
    if raw_paths:
        selected = [Path(part.strip()) for part in raw_paths.split(",") if part.strip()]
        selected = [path if path.is_absolute() else (PROJECT_ROOT / path) for path in selected]
        return [path for path in selected if path.exists()]
    raw_indexes = str(os.getenv("DOCUMENT_REVIEW_FINDINGS_EXPERIMENT_DOC_INDEXES", "")).strip()
    if raw_indexes:
        indexes: list[int] = []
        for part in raw_indexes.split(","):
            part = part.strip()
            if not part:
                continue
            indexes.append(int(part))
        selected = [DEFAULT_DOCUMENTS[index] for index in indexes if 0 <= index < len(DEFAULT_DOCUMENTS)]
        return selected or DEFAULT_DOCUMENTS[:1]
    max_docs = max(1, int(os.getenv("DOCUMENT_REVIEW_FINDINGS_EXPERIMENT_MAX_DOCS", "2")))
    return DEFAULT_DOCUMENTS[:max_docs]


def _filter_configs(configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_keys = str(os.getenv("DOCUMENT_REVIEW_FINDINGS_EXPERIMENT_CONFIG_KEYS", "")).strip()
    if not raw_keys:
        return configs
    wanted = {part.strip() for part in raw_keys.split(",") if part.strip()}
    filtered = [config for config in configs if str(config.get("key") or "") in wanted]
    return filtered or configs


def main() -> None:
    provider_registry = build_provider_registry()
    provider_entry = provider_registry.get("ollama") or {}
    embedding_provider = provider_entry.get("instance")
    if embedding_provider is None:
        raise RuntimeError("Ollama provider is required to run the Document Review findings experiment.")

    available_models = embedding_provider.list_available_models() if hasattr(embedding_provider, "list_available_models") else []
    nemotron_model = next((model for model in available_models if "nemotron" in model.lower() and "super" in model.lower()), None)
    if nemotron_model is None:
        nemotron_model = next((model for model in available_models if "nemotron" in model.lower()), None)
    base_model = "qwen2.5:7b" if "qwen2.5:7b" in available_models else (available_models[0] if available_models else None)
    if base_model is None:
        raise RuntimeError("No Ollama chat model is available for the experiment.")

    selected_documents = _selected_documents()
    configs: list[dict[str, Any]] = [
        {
            "key": "heuristic_baseline",
            "label": "Heuristic baseline",
            "base_model": base_model,
            "findings_model": None,
            "prompt_style": None,
            "synthesis_enabled": False,
        },
        {
            "key": f"{base_model.replace(':', '_')}_hybrid",
            "label": f"{base_model} hybrid",
            "base_model": base_model,
            "findings_model": base_model,
            "prompt_style": "hybrid",
            "synthesis_enabled": True,
        },
    ]
    if nemotron_model:
        for style in ("extractive", "executive", "hybrid"):
            configs.append(
                {
                    "key": f"nemotron_{style}",
                    "label": f"{nemotron_model} {style}",
                    "base_model": base_model,
                    "findings_model": nemotron_model,
                    "prompt_style": style,
                    "synthesis_enabled": True,
                }
            )

    configs = _filter_configs(configs)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = str(os.getenv("DOCUMENT_REVIEW_FINDINGS_EXPERIMENT_LABEL", "")).strip()
    output_name = f"document_review_findings_experiment_{label}_{timestamp}" if label else f"document_review_findings_experiment_{timestamp}"
    output_root = PROJECT_ROOT / "evals/benchmark-runs" / output_name
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_root / "progress.json",
        {
            "generated_at": datetime.now().isoformat(),
            "status": "running",
            "documents": [str(path.relative_to(PROJECT_ROOT)) for path in selected_documents],
            "configs": configs,
            "completed_runs": 0,
            "total_runs": len(selected_documents) * len(configs),
            "runs": [],
        },
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        rag_settings = replace(
            get_rag_settings(),
            store_path=Path(temp_dir) / ".rag_store.json",
            chroma_path=Path(temp_dir) / ".chroma_rag",
        )
        loaded_documents = [load_document(_UploadAdapter(path), rag_settings) for path in selected_documents]
        indexed_documents, index_status = index_loaded_documents(
            loaded_documents,
            rag_settings=rag_settings,
            provider_registry=provider_registry,
        )
        if not index_status.get("ok"):
            raise RuntimeError(f"Indexing failed: {index_status}")

        rag_index = normalize_rag_index(load_rag_store(rag_settings.store_path), rag_settings)
        document_id_by_name = {document.name: document.document_id for document in indexed_documents}
        experiment_runs: list[dict[str, Any]] = []

        patchers = (
            patch("src.providers.registry.build_provider_registry", return_value=provider_registry),
            patch("src.services.document_context._get_rag_index", return_value=rag_index),
            patch("src.services.document_context._get_effective_rag_settings", return_value=rag_settings),
            patch("src.services.document_context._get_embedding_provider", return_value=embedding_provider),
        )
        with patchers[0], patchers[1], patchers[2], patchers[3]:
            total_runs = len(selected_documents) * len(configs)
            completed_runs = 0
            for document_path in selected_documents:
                document_id = document_id_by_name[document_path.name]
                for config in configs:
                    run_started_at = time.perf_counter()
                    completed_runs += 1
                    print(
                        f"[document-review-experiment] run {completed_runs}/{total_runs} | document={document_path.name} | config={config['key']}",
                        flush=True,
                    )
                    telemetry = {
                        "product_workflow_id": "document_review",
                        "agent_intent": "document_risk_review",
                        "agent_intent_reason": "document_review_findings_experiment_forced_risk_review",
                        "agent_tool": "review_document_risks",
                        "agent_tool_reason": "document_review_findings_experiment_forced_risk_review",
                        "agent_answer_mode": "friendly",
                        "document_review_findings_synthesis_enabled": config["synthesis_enabled"],
                    }
                    if config["findings_model"]:
                        telemetry["document_review_findings_model_override"] = config["findings_model"]
                    if config["prompt_style"]:
                        telemetry["document_review_findings_prompt_style"] = config["prompt_style"]

                    request = TaskExecutionRequest(
                        task_type="document_agent",
                        input_text=RISK_REVIEW_QUERY,
                        use_rag_context=False,
                        use_document_context=True,
                        source_document_ids=[document_id],
                        context_strategy="retrieval",
                        provider="ollama",
                        model=config["base_model"],
                        temperature=0.2,
                        telemetry=telemetry,
                    )
                    structured_result = run_structured_execution_workflow(
                        request,
                        strategy="langgraph_context_retry",
                    )
                    result = _build_result_from_structured(structured_result)
                    view = build_document_review_view(result)
                    scores = _evaluate_view(result, view)
                    findings_synthesis_metadata = (
                        result.structured_result.validated_output.structured_response.get("findings_synthesis_metadata")
                        if isinstance(result.structured_result.validated_output, DocumentAgentPayload)
                        and isinstance(result.structured_result.validated_output.structured_response, dict)
                        else None
                    )
                    experiment_runs.append(
                        {
                            "document": document_path.name,
                            "document_path": str(document_path.relative_to(PROJECT_ROOT)),
                            "config": config,
                            "duration_s": round(time.perf_counter() - run_started_at, 3),
                            "structured_success": structured_result.success,
                            "status": result.status,
                            "summary": result.summary,
                            "warnings": result.warnings,
                            "findings_synthesis_metadata": findings_synthesis_metadata,
                            "synthesis_success": _synthesis_success(findings_synthesis_metadata),
                            "promotion_score": _promotion_score(
                                raw_score=float(scores.get("total_score") or 0.0),
                                config=config,
                                metadata=findings_synthesis_metadata,
                            ),
                            "scores": scores,
                            "view": view,
                        }
                    )
                    _write_json(
                        output_root / "progress.json",
                        {
                            "generated_at": datetime.now().isoformat(),
                            "status": "running",
                            "documents": [str(path.relative_to(PROJECT_ROOT)) for path in selected_documents],
                            "configs": configs,
                            "completed_runs": completed_runs,
                            "total_runs": total_runs,
                            "runs": experiment_runs,
                        },
                    )

    aggregated: dict[str, list[float]] = {}
    promotion_aggregated: dict[str, list[float]] = {}
    synthesis_aggregated: dict[str, list[float]] = {}
    for run in experiment_runs:
        aggregated.setdefault(run["config"]["key"], []).append(float(run["scores"]["total_score"]))
        promotion_aggregated.setdefault(run["config"]["key"], []).append(float(run.get("promotion_score") or 0.0))
        if bool(run.get("config", {}).get("synthesis_enabled")):
            synthesis_aggregated.setdefault(run["config"]["key"], []).append(float(run.get("promotion_score") or 0.0))
    ranking = sorted(
        [
            {
                "config_key": key,
                "avg_total_score": round(mean(values), 4),
                "runs": len(values),
            }
            for key, values in aggregated.items()
        ],
        key=lambda item: item["avg_total_score"],
        reverse=True,
    )
    promotion_ranking = sorted(
        [
            {
                "config_key": key,
                "avg_promotion_score": round(mean(values), 4),
                "runs": len(values),
            }
            for key, values in promotion_aggregated.items()
        ],
        key=lambda item: item["avg_promotion_score"],
        reverse=True,
    )
    synthesis_ranking = sorted(
        [
            {
                "config_key": key,
                "avg_promotion_score": round(mean(values), 4),
                "runs": len(values),
            }
            for key, values in synthesis_aggregated.items()
        ],
        key=lambda item: item["avg_promotion_score"],
        reverse=True,
    )
    winning_strategy = synthesis_ranking[0] if synthesis_ranking else (promotion_ranking[0] if promotion_ranking else None)

    report_payload = {
        "generated_at": datetime.now().isoformat(),
        "documents": [str(path.relative_to(PROJECT_ROOT)) for path in selected_documents],
        "configs": configs,
        "ranking": ranking,
        "promotion_ranking": promotion_ranking,
        "synthesis_ranking": synthesis_ranking,
        "winner": winning_strategy,
        "runs": experiment_runs,
    }
    _write_json(output_root / "results.json", report_payload)
    _write_json(
        output_root / "progress.json",
        {
            **report_payload,
            "status": "completed",
            "completed_runs": len(experiment_runs),
            "total_runs": len(selected_documents) * len(configs),
        },
    )

    lines = [
        "# Document Review Findings Experiment",
        "",
        f"Generated at: {report_payload['generated_at']}",
        "",
        "## Documents",
        *[f"- `{item}`" for item in report_payload["documents"]],
        "",
        "## Ranking",
    ]
    for item in ranking:
        lines.append(f"- `{item['config_key']}` -> avg_total_score={item['avg_total_score']} over {item['runs']} run(s)")
    lines.extend(["", "## Promotion ranking"])
    for item in promotion_ranking:
        lines.append(f"- `{item['config_key']}` -> avg_promotion_score={item['avg_promotion_score']} over {item['runs']} run(s)")
    lines.extend(["", "## Synthesis ranking"])
    for item in synthesis_ranking:
        lines.append(f"- `{item['config_key']}` -> avg_promotion_score={item['avg_promotion_score']} over {item['runs']} run(s)")
    lines.extend(["", "## Winning strategy", f"- `{winning_strategy['config_key']}`" if winning_strategy else "- none"])
    (output_root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output_root": str(output_root), "winner": winning_strategy}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
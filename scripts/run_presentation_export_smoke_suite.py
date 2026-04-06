from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import PresentationExportSettings
from src.services.presentation_export import (
    ACTION_PLAN_EXPORT_KIND,
    CANDIDATE_REVIEW_EXPORT_KIND,
    DEFAULT_PRESENTATION_EXPORT_KIND,
    DOCUMENT_REVIEW_EXPORT_KIND,
    EVIDENCE_PACK_EXPORT_KIND,
    POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
)
from src.services.presentation_export_service import generate_executive_deck
from src.structured.base import AgentSource, CVAnalysisPayload, ComparisonFinding, ContactInfo, DocumentAgentPayload
from src.structured.envelope import StructuredResult


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sample_model_comparison_entries() -> list[dict[str, object]]:
    return [
        {
            "benchmark_use_case": "executive_summary",
            "prompt_profile": "neutral",
            "response_format": "bullet_list",
            "retrieval_strategy": "manual_hybrid",
            "embedding_provider": "ollama",
            "embedding_model": "embeddinggemma:300m",
            "use_documents": True,
            "aggregate": {
                "total_candidates": 2,
                "success_rate": 1.0,
                "avg_latency_s": 0.95,
                "avg_output_chars": 80.0,
                "avg_format_adherence": 0.95,
                "avg_groundedness_score": 0.74,
                "avg_schema_adherence": 0.0,
                "avg_use_case_fit_score": 0.89,
            },
            "candidate_results": [
                {
                    "provider_effective": "ollama",
                    "model_effective": "qwen2.5:7b",
                    "runtime_bucket": "local",
                    "quantization_family": "unspecified_local",
                    "success": True,
                    "latency_s": 1.1,
                    "output_chars": 120,
                    "format_adherence": 1.0,
                    "groundedness_score": 0.8,
                    "use_case_fit_score": 0.9,
                },
                {
                    "provider_effective": "openai",
                    "model_effective": "gpt-4o-mini",
                    "runtime_bucket": "cloud",
                    "quantization_family": "cloud_managed",
                    "success": True,
                    "latency_s": 0.8,
                    "output_chars": 100,
                    "format_adherence": 0.9,
                    "groundedness_score": 0.68,
                    "use_case_fit_score": 0.88,
                },
            ],
        }
    ]


def _sample_eval_entries() -> list[dict[str, object]]:
    return [
        {
            "suite_name": "structured_smoke_eval",
            "task_type": "summary",
            "case_name": "fixture:summary",
            "provider": "ollama",
            "model": "qwen2.5:7b",
            "status": "PASS",
            "score": 5,
            "max_score": 5,
            "latency_s": 1.2,
            "needs_review": False,
        },
        {
            "suite_name": "checklist_regression",
            "task_type": "checklist",
            "case_name": "fixture:checklist",
            "provider": "ollama",
            "model": "qwen2.5:7b",
            "status": "WARN",
            "score": 8,
            "max_score": 10,
            "latency_s": 2.4,
            "needs_review": True,
        },
    ]


def _sample_document_agent_result() -> StructuredResult:
    payload = DocumentAgentPayload(
        task_type="document_agent",
        agent_label="Document Operations Copilot",
        user_intent="policy_review",
        intent_reason="Document asks for a grounded compliance review.",
        answer_mode="review",
        tool_used="policy_compliance",
        summary="The policy adds new obligations and still depends on final legal validation.",
        key_points=[
            "New formal approval obligation.",
            "The owner for the annual control has not yet been defined.",
        ],
        limitations=["Final legal validation is still pending."],
        recommended_actions=["Define the control owner.", "Review critical clauses with legal."],
        guardrails_applied=["Human review required for final policy decision."],
        available_tools=[],
        compared_documents=["Policy 2025", "Policy 2026"],
        comparison_findings=[
            ComparisonFinding(
                finding_type="obligation_change",
                title="Formal approval became mandatory",
                description="The 2026 version requires formal approval for supplier onboarding.",
                documents=["Policy 2025", "Policy 2026"],
                evidence=["Page 4 - approval formal required"],
            )
        ],
        checklist_preview=["Define owner", "Validate legal sign-off"],
        structured_response={
            "review_type": "policy_compliance",
            "gaps": ["Legal sign-off still missing"],
            "actions": ["Define the annual control owner"],
            "extraction_payload": {
                "risks": [
                    {
                        "description": "Owner not defined for the annual control",
                        "owner": "Compliance",
                        "due_date": "2026-04-10",
                        "evidence": "Page 12",
                    }
                ],
                "action_items": [
                    {
                        "description": "Define the annual control owner",
                        "owner": "Compliance",
                        "due_date": "2026-04-10",
                        "status": "open",
                    }
                ],
                "missing_information": ["Legal sign-off still missing"],
            },
        },
        sources=[
            AgentSource(
                source="Policy_2026.pdf",
                document_id="policy_2026",
                snippet="Formal approval is required for supplier onboarding.",
            )
        ],
        tool_runs=[],
        confidence=0.82,
        needs_review=True,
        needs_review_reason="legal_signoff_missing",
    )
    return StructuredResult(
        success=True,
        task_type="document_agent",
        validated_output=payload,
        source_documents=["policy_2026"],
    )


def _sample_cv_analysis_result() -> StructuredResult:
    payload = CVAnalysisPayload(
        task_type="cv_analysis",
        personal_info=ContactInfo(full_name="Jane Doe", location="São Paulo", email="jane@example.com"),
        skills=["Python", "RAG", "Structured outputs"],
        languages=["English", "Portuguese"],
        education_entries=[
            {
                "degree": "BSc Computer Science",
                "institution": "USP",
                "date_range": "2018-2022",
                "location": "São Paulo",
            }
        ],
        experience_entries=[
            {
                "title": "Applied AI Engineer",
                "organization": "Acme",
                "date_range": "2022-2025",
                "bullets": ["Built RAG pipelines", "Shipped eval-driven AI features"],
            }
        ],
        experience_years=3.5,
        strengths=["Strong applied AI execution", "Good product + engineering bridge"],
        improvement_areas=["Validate scale/production depth"],
    )
    return StructuredResult(
        success=True,
        task_type="cv_analysis",
        validated_output=payload,
        source_documents=["cv_jane_doe"],
    )


def _sample_action_entries() -> list[dict[str, object]]:
    return [
        {
            "action_type": "recommended_action",
            "description": "Define the annual control owner",
            "owner": "Compliance",
            "due_date": "2026-04-10",
            "status": "open",
            "review_type": "risk_gap_review",
        },
        {
            "action_type": "recommended_action",
            "description": "Validate legal sign-off",
            "owner": "Legal",
            "due_date": "2026-04-12",
            "status": "in_progress",
            "review_type": "risk_gap_review",
        },
    ]


def _sample_evidenceops_worklog_entries() -> list[dict[str, object]]:
    return [
        {
            "review_type": "risk_gap_review",
            "summary": "EvidenceOps found findings and open actions.",
            "workflow_id": "wf_123",
            "findings": [
                {
                    "finding_type": "risk",
                    "title": "Missing annual control evidence",
                    "description": "Annual control evidence is missing",
                    "evidence": ["Doc A / page 4"],
                }
            ],
            "action_items": [
                {
                    "action_type": "recommended_action",
                    "description": "Update evidence register",
                    "owner": "Compliance",
                    "due_date": "2026-04-12",
                    "status": "open",
                }
            ],
            "recommended_actions": ["Update evidence register"],
            "limitations": ["One piece of evidence still depends on manual validation"],
        }
    ]


def _load_review_metrics(result: dict[str, Any]) -> dict[str, Any]:
    review_path = result.get("local_review_path")
    if not review_path:
        return {}
    path = Path(review_path)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        "average_score": payload.get("average_score"),
        "status": payload.get("status"),
        "issue_count": payload.get("issue_count"),
        "top_risk_slides": payload.get("top_risk_slides"),
    }


def _build_settings(output_dir: Path, base_url: str) -> PresentationExportSettings:
    return PresentationExportSettings(
        enabled=True,
        base_url=base_url,
        timeout_seconds=120,
        remote_output_dir="outputs/ai_workbench_export_smoke_suite",
        remote_preview_dir="outputs/ai_workbench_export_smoke_suite_previews",
        local_artifact_dir=output_dir,
        include_review=True,
        preview_backend="auto",
        require_real_previews=False,
        fail_on_regression=False,
    )


def _ensure_ppt_creator_api(ppt_creator_root: Path):
    sys.path.insert(0, str(ppt_creator_root))
    from ppt_creator.api import preview_pptx_payload, render_spec_payload

    return render_spec_payload, preview_pptx_payload


def run_suite(*, output_dir: Path, base_url: str, ppt_creator_root: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    settings = _build_settings(output_dir, base_url)
    render_spec_payload, preview_pptx_payload = _ensure_ppt_creator_api(ppt_creator_root)
    asset_root = ppt_creator_root / "examples"

    doc_result = _sample_document_agent_result()
    cv_result = _sample_cv_analysis_result()
    action_entries = _sample_action_entries()
    worklog_entries = _sample_evidenceops_worklog_entries()

    deck_cases: list[tuple[str, dict[str, Any]]] = [
        (
            DEFAULT_PRESENTATION_EXPORT_KIND,
            {
                "model_comparison_entries": _sample_model_comparison_entries(),
                "eval_entries": _sample_eval_entries(),
            },
        ),
        (DOCUMENT_REVIEW_EXPORT_KIND, {"structured_result": doc_result}),
        (POLICY_CONTRACT_COMPARISON_EXPORT_KIND, {"structured_result": doc_result}),
        (ACTION_PLAN_EXPORT_KIND, {"evidenceops_action_entries": action_entries}),
        (CANDIDATE_REVIEW_EXPORT_KIND, {"structured_result": cv_result}),
        (
            EVIDENCE_PACK_EXPORT_KIND,
            {
                "evidenceops_worklog_entries": worklog_entries,
                "evidenceops_action_entries": action_entries,
            },
        ),
    ]

    summary: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "renderer_base_url": base_url,
        "cases": [],
    }

    for export_kind, kwargs in deck_cases:
        result = generate_executive_deck(export_kind=export_kind, settings=settings, **kwargs)
        artifact_dir = Path(result["local_artifact_dir"])
        local_preview_summary: dict[str, Any] = {}
        local_fallback_render: dict[str, Any] = {}
        local_pptx_path = result.get("local_pptx_path")
        payload_path = result.get("local_payload_path")

        if payload_path and Path(payload_path).exists() and not (local_pptx_path and Path(local_pptx_path).exists()):
            try:
                payload = json.loads(Path(payload_path).read_text(encoding="utf-8"))
                fallback_output_path = artifact_dir / f"{export_kind}_local_fallback.pptx"
                fallback_preview_dir = artifact_dir / "local_fallback_previews"
                fallback_result = render_spec_payload(
                    payload,
                    output_path=fallback_output_path,
                    asset_root=asset_root,
                    include_review=True,
                    preview_output_dir=fallback_preview_dir,
                    preview_backend="auto",
                    preview_require_real=False,
                    preview_fail_on_regression=False,
                )
                _write_json(artifact_dir / "local_fallback_render_response.json", fallback_result)
                quality_review = fallback_result.get("quality_review") if isinstance(fallback_result.get("quality_review"), dict) else {}
                preview_result = fallback_result.get("preview_result") if isinstance(fallback_result.get("preview_result"), dict) else {}
                local_fallback_render = {
                    "used": True,
                    "output_path": fallback_result.get("output_path"),
                    "average_score": quality_review.get("average_score"),
                    "status": quality_review.get("status"),
                    "issue_count": quality_review.get("issue_count"),
                    "top_risk_slides": quality_review.get("top_risk_slides"),
                    "preview_output_dir": str(fallback_preview_dir),
                    "thumbnail_sheet": preview_result.get("thumbnail_sheet"),
                    "preview_count": preview_result.get("preview_count"),
                    "first_preview": (preview_result.get("previews") or [None])[0],
                    "preview_artifact_review": preview_result.get("preview_artifact_review"),
                }
                local_pptx_path = str(fallback_output_path)
            except Exception as error:  # noqa: BLE001
                local_fallback_render = {"used": False, "fallback_error": str(error)}

        if local_pptx_path and Path(local_pptx_path).exists():
            preview_output_dir = artifact_dir / "local_previews"
            try:
                preview_result = preview_pptx_payload(
                    local_pptx_path,
                    output_dir=preview_output_dir,
                    require_real_previews=False,
                    fail_on_regression=False,
                )
                local_preview_summary = {
                    "preview_output_dir": str(preview_output_dir),
                    "thumbnail_sheet": preview_result.get("thumbnail_sheet"),
                    "preview_count": preview_result.get("preview_count"),
                    "first_preview": (preview_result.get("previews") or [None])[0],
                    "preview_artifact_review": preview_result.get("preview_artifact_review"),
                }
            except Exception as error:  # noqa: BLE001
                local_preview_summary = {"preview_error": str(error), "preview_output_dir": str(preview_output_dir)}

        review_metrics = _load_review_metrics(result)
        summary["cases"].append(
            {
                "export_kind": export_kind,
                "status": result.get("status"),
                "artifact_dir": result.get("local_artifact_dir"),
                "contract_path": result.get("local_contract_path"),
                "payload_path": result.get("local_payload_path"),
                "pptx_path": result.get("local_pptx_path") or local_fallback_render.get("output_path"),
                "thumbnail_sheet": result.get("local_thumbnail_sheet_path"),
                "preview_manifest_path": result.get("local_preview_manifest_path"),
                "warnings": result.get("warnings"),
                "error_message": result.get("error_message"),
                **review_metrics,
                "local_preview_artifacts": local_preview_summary,
                "local_fallback_render": local_fallback_render,
            }
        )

    summary_path = output_dir / "suite_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"summary_path": str(summary_path), **summary}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a smoke suite for the current executive deck generation flows.")
    parser.add_argument(
        "--output-dir",
        default=str(Path("artifacts") / "presentation_exports" / "executive_deck_smoke_suite"),
        help="Directory where the generated artifact suite will be stored.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8787",
        help="Local renderer host base URL.",
    )
    parser.add_argument(
        "--ppt-creator-root",
        default="/Users/danyellambert/ppt_creator_app",
        help="Absolute path to the ppt_creator_app repository used to generate local previews from PPTX artifacts.",
    )
    args = parser.parse_args()

    result = run_suite(
        output_dir=Path(args.output_dir),
        base_url=args.base_url,
        ppt_creator_root=Path(args.ppt_creator_root),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
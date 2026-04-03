from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any

from src.config import get_rag_settings
from src.evals.phase8_thresholds import CHECKLIST_REGRESSION_THRESHOLDS
from src.storage.phase8_eval_store import append_eval_run
from src.storage.rag_store import load_rag_store
from src.structured.envelope import TaskExecutionRequest
from src.structured.service import structured_service


FIXTURE_DEFAULT = PROJECT_ROOT / "phase5_eval" / "fixtures" / "06_checklist_who_surgical_gold.json"
REPORTS_DIR = PROJECT_ROOT / "phase5_eval" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DB_PATH = PROJECT_ROOT / ".phase8_eval_runs.sqlite3"


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rag_store() -> dict[str, Any]:
    settings = get_rag_settings()
    rag_store = load_rag_store(settings.store_path)
    if not isinstance(rag_store, dict):
        raise RuntimeError(f"RAG store not found or invalid at {settings.store_path}")
    return rag_store


def _resolve_document(rag_store: dict[str, Any], *, document_id: str | None, document_name: str | None) -> dict[str, Any]:
    documents = [doc for doc in rag_store.get("documents", []) if isinstance(doc, dict)]
    if document_id:
        for document in documents:
            if str(document.get("document_id") or "") == document_id:
                return document
        raise RuntimeError(f"Document id not found in rag store: {document_id}")

    normalized_target = _normalize_text(document_name)
    exact = [doc for doc in documents if _normalize_text(doc.get("name")) == normalized_target]
    if exact:
        return exact[0]
    partial = [doc for doc in documents if normalized_target and normalized_target in _normalize_text(doc.get("name"))]
    if partial:
        return partial[0]
    raise RuntimeError(f"Document name not found in rag store: {document_name}")


def _item_match_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("title"),
        item.get("description"),
        item.get("source_text"),
        item.get("category"),
    ]
    return _normalize_text(" ".join(str(part or "") for part in parts))


def _matches_expected(item_text: str, expected: dict[str, Any]) -> bool:
    aliases = [_normalize_text(alias) for alias in expected.get("aliases", [])]
    required_terms = [_normalize_text(term) for term in expected.get("required_terms", [])]
    if any(alias and alias in item_text for alias in aliases):
        return True
    if required_terms and all(term and term in item_text for term in required_terms):
        return True
    return False


def _is_collapsed_match_group(matches: list[dict[str, Any]]) -> bool:
    if len(matches) <= 1:
        return False
    expected_indexes = [int(item.get("expected_index") or 0) for item in matches]
    phases = {str(item.get("phase") or "") for item in matches if item.get("phase")}
    if len(phases) == 1:
        return True
    return (max(expected_indexes) - min(expected_indexes)) <= 2


def _is_artifact_item(item: dict[str, Any]) -> bool:
    title = _normalize_text(item.get("title"))
    description = _normalize_text(item.get("description"))
    source_text = _normalize_text(item.get("source_text"))
    artifact_patterns = (
        title.startswith("category="),
        description.startswith("category="),
        source_text.startswith("category="),
        title == "category=-",
        title == "-",
    )
    return any(artifact_patterns)


def _style_issue_item(item: dict[str, Any]) -> bool:
    title = str(item.get("title") or "")
    description = str(item.get("description") or "")
    return title.strip().startswith("- ") or description.strip().startswith("- ")


def _evaluate_checklist_payload(payload: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    expected_sequence = fixture.get("expected_sequence", [])
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    item_texts = [_item_match_text(item) for item in items]
    grounded_items = [item for item in items if _normalize_text(item.get("source_text")) or _normalize_text(item.get("evidence"))]
    citation_ready_items = [item for item in items if _normalize_text(item.get("source_text")) and _normalize_text(item.get("evidence"))]

    id_counts = Counter(str(item.get("id") or "") for item in items if item.get("id"))
    duplicate_ids = sorted(item_id for item_id, count in id_counts.items() if count > 1)
    artifact_items = [index for index, item in enumerate(items) if _is_artifact_item(item)]
    style_issue_items = [index for index, item in enumerate(items) if _style_issue_item(item)]

    matched: list[dict[str, Any]] = []
    missing: list[str] = []
    unmatched_indexes = set(range(len(items)))
    last_index = -1
    order_breaks: list[dict[str, Any]] = []

    for expected in expected_sequence:
        found_index = None
        for index in sorted(unmatched_indexes):
            if index <= last_index:
                continue
            if _matches_expected(item_texts[index], expected):
                found_index = index
                break
        if found_index is None:
            for index in sorted(unmatched_indexes):
                if _matches_expected(item_texts[index], expected):
                    found_index = index
                    order_breaks.append({
                        "expected_id": expected.get("id"),
                        "matched_item_index": index,
                        "reason": "matched_out_of_order",
                    })
                    break
        if found_index is None:
            missing.append(str(expected.get("id") or "unknown"))
            continue
        matched.append({
            "expected_id": expected.get("id"),
            "phase": expected.get("phase"),
            "matched_item_index": found_index,
            "matched_title": items[found_index].get("title"),
        })
        unmatched_indexes.discard(found_index)
        last_index = max(last_index, found_index)

    collapsed_items: list[dict[str, Any]] = []
    for index, item_text in enumerate(item_texts):
        matched_expected_rows = [
            {
                "expected_id": str(expected.get("id")),
                "expected_index": expected_index,
                "phase": expected.get("phase"),
            }
            for expected_index, expected in enumerate(expected_sequence)
            if _matches_expected(item_text, expected)
        ]
        if _is_collapsed_match_group(matched_expected_rows):
            collapsed_items.append({
                "item_index": index,
                "title": items[index].get("title"),
                "matched_expected_ids": [row["expected_id"] for row in matched_expected_rows],
            })

    unexpected_items = [
        {
            "item_index": index,
            "title": items[index].get("title"),
            "category": items[index].get("category"),
        }
        for index in sorted(unmatched_indexes)
        if index not in artifact_items
    ]

    coverage = len(matched) / max(len(expected_sequence), 1)
    grounded_item_rate = round(len(grounded_items) / max(len(items), 1), 4) if items else 0.0
    citation_precision_proxy = round(len(citation_ready_items) / max(len(items), 1), 4) if items else 0.0
    status = "PASS"
    reasons: list[str] = []
    if duplicate_ids:
        status = "FAIL"
        reasons.append(f"duplicate item ids detected: {duplicate_ids}")
    if artifact_items:
        status = "FAIL"
        reasons.append(f"artifact items detected at indexes: {artifact_items}")
    if collapsed_items:
        status = "FAIL"
        reasons.append(f"collapsed items detected: {len(collapsed_items)}")
    if coverage < float(CHECKLIST_REGRESSION_THRESHOLDS.get("warn_min_coverage") or 0.75):
        status = "FAIL"
        reasons.append(f"coverage too low: {coverage:.2%}")
    elif coverage < float(CHECKLIST_REGRESSION_THRESHOLDS.get("pass_min_coverage") or 0.9) and status != "FAIL":
        status = "WARN"
        reasons.append(f"coverage below target: {coverage:.2%}")
    if grounded_item_rate < float(CHECKLIST_REGRESSION_THRESHOLDS.get("warn_min_grounded_item_rate") or 0.65):
        status = "FAIL"
        reasons.append(f"grounded item rate too low: {grounded_item_rate:.2%}")
    elif grounded_item_rate < float(CHECKLIST_REGRESSION_THRESHOLDS.get("pass_min_grounded_item_rate") or 0.85) and status != "FAIL":
        status = "WARN"
        reasons.append(f"grounded item rate below target: {grounded_item_rate:.2%}")
    if citation_precision_proxy < float(CHECKLIST_REGRESSION_THRESHOLDS.get("warn_min_citation_precision_proxy") or 0.55):
        status = "FAIL"
        reasons.append(f"citation precision proxy too low: {citation_precision_proxy:.2%}")
    elif citation_precision_proxy < float(CHECKLIST_REGRESSION_THRESHOLDS.get("pass_min_citation_precision_proxy") or 0.75) and status != "FAIL":
        status = "WARN"
        reasons.append(f"citation precision proxy below target: {citation_precision_proxy:.2%}")
    if order_breaks and status == "PASS":
        status = "WARN"
        reasons.append(f"order breaks detected: {len(order_breaks)}")
    if unexpected_items and status == "PASS":
        status = "WARN"
        reasons.append(f"unexpected unmatched items: {len(unexpected_items)}")

    return {
        "status": status,
        "coverage": round(coverage, 4),
        "grounded_item_rate": grounded_item_rate,
        "citation_precision_proxy": citation_precision_proxy,
        "thresholds": CHECKLIST_REGRESSION_THRESHOLDS,
        "expected_items": len(expected_sequence),
        "matched_items": len(matched),
        "missing_items": missing,
        "matched": matched,
        "duplicate_ids": duplicate_ids,
        "artifact_items": artifact_items,
        "style_issue_items": style_issue_items,
        "order_breaks": order_breaks,
        "collapsed_items": collapsed_items,
        "unexpected_items": unexpected_items,
        "reasons": reasons,
    }


def _save_report(report: dict[str, Any]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORTS_DIR / f"checklist_regression_{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _extract_latency_s(result) -> float | None:
    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
    telemetry = metadata.get("telemetry") if isinstance(metadata.get("telemetry"), dict) else {}
    timings = telemetry.get("timings_s") if isinstance(telemetry.get("timings_s"), dict) else {}
    workflow_total = metadata.get("workflow_total_s")
    if isinstance(workflow_total, (int, float)):
        return round(float(workflow_total), 4)
    total_s = timings.get("total_s")
    if isinstance(total_s, (int, float)):
        return round(float(total_s), 4)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run checklist regression evaluation against a fixed PDF fixture.")
    parser.add_argument("--fixture", default=str(FIXTURE_DEFAULT))
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--model", default=None)
    parser.add_argument("--document-id", default=None)
    parser.add_argument("--document-name", default=None)
    parser.add_argument("--context-strategy", default="document_scan", choices=["document_scan", "retrieval"])
    parser.add_argument("--dry-run", action="store_true", help="Resolve fixture and document only, without calling the model.")
    args = parser.parse_args()

    fixture = _load_fixture(Path(args.fixture))
    rag_store = _load_rag_store()
    document = _resolve_document(
        rag_store,
        document_id=args.document_id,
        document_name=args.document_name or fixture.get("document_name"),
    )

    if args.dry_run:
        payload = {
            "fixture": str(Path(args.fixture)),
            "resolved_document": {
                "document_id": document.get("document_id"),
                "name": document.get("name"),
                "file_type": document.get("file_type"),
                "chunk_count": document.get("chunk_count"),
            },
            "input_text": fixture.get("input_text"),
            "expected_items": len(fixture.get("expected_sequence", [])),
            "context_strategy": args.context_strategy,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    request = TaskExecutionRequest(
        task_type="checklist",
        input_text=str(fixture.get("input_text") or ""),
        use_document_context=True,
        source_document_ids=[str(document.get("document_id"))],
        context_strategy=args.context_strategy,
        provider=args.provider,
        model=args.model,
    )
    result = structured_service.execute_task(request)

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "fixture": str(Path(args.fixture)),
        "eval_store_path": str(EVAL_DB_PATH),
        "provider": args.provider,
        "model": args.model,
        "context_strategy": args.context_strategy,
        "resolved_document": {
            "document_id": document.get("document_id"),
            "name": document.get("name"),
            "file_type": document.get("file_type"),
            "chunk_count": document.get("chunk_count"),
        },
        "success": result.success,
        "validation_error": result.validation_error,
        "parsing_error": result.parsing_error,
        "execution_metadata": result.execution_metadata,
        "payload": result.validated_output.model_dump(mode="json") if result.validated_output else None,
    }

    if result.success and result.validated_output is not None:
        report["evaluation"] = _evaluate_checklist_payload(
            result.validated_output.model_dump(mode="json"),
            fixture,
        )
    else:
        report["evaluation"] = {
            "status": "FAIL",
            "reasons": ["structured execution failed before checklist evaluation"],
        }

    evaluation = report["evaluation"] if isinstance(report.get("evaluation"), dict) else {}
    append_eval_run(
        EVAL_DB_PATH,
        {
            "suite_name": "checklist_regression",
            "task_type": "checklist",
            "case_name": str(document.get("name") or Path(args.fixture).name),
            "provider": args.provider,
            "model": args.model,
            "status": str(evaluation.get("status") or "FAIL"),
            "score": int(evaluation.get("matched_items") or 0),
            "max_score": int(evaluation.get("expected_items") or 0),
            "quality_score": result.quality_score,
            "overall_confidence": result.overall_confidence,
            "latency_s": _extract_latency_s(result),
            "needs_review": bool((result.execution_metadata or {}).get("needs_review")) if isinstance(result.execution_metadata, dict) else False,
            "context_strategy": args.context_strategy,
            "metrics": {
                "coverage": evaluation.get("coverage"),
                "grounded_item_rate": evaluation.get("grounded_item_rate"),
                "citation_precision_proxy": evaluation.get("citation_precision_proxy"),
                "duplicate_ids": len(evaluation.get("duplicate_ids") or []),
                "artifact_items": len(evaluation.get("artifact_items") or []),
                "collapsed_items": len(evaluation.get("collapsed_items") or []),
                "style_issue_items": len(evaluation.get("style_issue_items") or []),
            },
            "reasons": evaluation.get("reasons") or [],
            "metadata": {
                "fixture": str(Path(args.fixture)),
                "document_id": document.get("document_id"),
                "thresholds": CHECKLIST_REGRESSION_THRESHOLDS,
            },
        },
    )

    out = _save_report(report)
    print(f"Report saved to: {out}")
    print(json.dumps(report["evaluation"], ensure_ascii=False, indent=2))

    status = str(report["evaluation"].get("status") or "FAIL")
    if status == "PASS":
        return 0
    if status == "WARN":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
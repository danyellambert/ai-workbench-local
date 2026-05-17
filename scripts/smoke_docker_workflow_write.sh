#!/usr/bin/env bash
set -euo pipefail

API_PORT="${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT:-8013}"
BASE_URL="${AI_DECISION_STUDIO_PRODUCT_API_BASE_URL:-http://127.0.0.1:${API_PORT}}"
REPORT_OUT="${AI_DECISION_STUDIO_DOCKER_WORKFLOW_WRITE_REPORT:-runtime/ai_decision_studio_functional_baseline/current_docker_workflow_write_smoke_report.json}"
WORKFLOW_ID="${AI_DECISION_STUDIO_WRITE_SMOKE_WORKFLOW_ID:-document_review}"
DOCUMENT_ID="${AI_DECISION_STUDIO_WRITE_SMOKE_DOCUMENT_ID:-}"

echo "== Docker workflow write smoke =="
echo "base_url=$BASE_URL"
echo "workflow_id=$WORKFLOW_ID"
echo "document_id=${DOCUMENT_ID:-auto}"
echo "report=$REPORT_OUT"

echo
echo "== Health =="
curl -fsS "$BASE_URL/health" | python3 -m json.tool

echo
echo "== Run workflow write smoke =="
BASE_URL="$BASE_URL" REPORT_OUT="$REPORT_OUT" WORKFLOW_ID="$WORKFLOW_ID" DOCUMENT_ID="$DOCUMENT_ID" python3 - <<'PY'
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

base = os.environ["BASE_URL"].rstrip("/")
report_path = Path(os.environ["REPORT_OUT"])
workflow_id = os.environ.get("WORKFLOW_ID") or "document_review"
explicit_document_id = (os.environ.get("DOCUMENT_ID") or "").strip()

def get_json(path, timeout=60):
    with urlopen(f"{base}{path}", timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def post_json(path, payload, timeout=240):
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

result = {
    "ok": False,
    "base_url": base,
    "workflow_id": workflow_id,
    "selected_document": None,
    "before": {},
    "after": {},
    "workflow_response": None,
    "error": None,
}

try:
    docs_payload = get_json("/api/product/document-library")
    documents = docs_payload.get("documents") or []
    indexed = [doc for doc in documents if doc.get("status") in {"indexed", "warning"}]

    if explicit_document_id:
        selected = next((doc for doc in indexed if doc.get("document_id") == explicit_document_id), None)
        if not selected:
            raise RuntimeError(f"Requested document is not indexed or not found: {explicit_document_id}")
    else:
        selected = indexed[0] if indexed else None

    if not selected:
        raise RuntimeError("No indexed documents available")

    doc_id = selected.get("document_id")
    result["selected_document"] = {
        "document_id": doc_id,
        "name": selected.get("name") or selected.get("filename") or selected.get("title"),
        "status": selected.get("status"),
        "chunk_count": selected.get("chunk_count"),
    }

    before_history = get_json("/api/product/run-history")
    before_runs = before_history.get("runs") or []
    result["before"] = {
        "returned_run_count": len(before_runs),
        "latest_run_id": before_runs[0].get("id") if before_runs else None,
    }

    payload = {
        "workflow_id": workflow_id,
        "document_ids": [doc_id],
        "input_text": "Run a concise Docker write smoke document review. Focus on policy obligations, risks, and evidence-backed findings.",
        "context_strategy": "document_scan",
        "use_document_context": True,
    }

    workflow_response = post_json("/api/product/run-workflow", payload)
    run_id = workflow_response.get("run_id")
    result_payload = workflow_response.get("result") if isinstance(workflow_response.get("result"), dict) else {}
    grounding_preview = result_payload.get("grounding_preview") if isinstance(result_payload, dict) else {}

    result["workflow_response"] = {
        "ok": workflow_response.get("ok"),
        "run_id": run_id,
        "top_keys": sorted(workflow_response.keys()),
        "result_keys": sorted(result_payload.keys()),
        "grounding_source_block_count": grounding_preview.get("source_block_count") if isinstance(grounding_preview, dict) else None,
        "grounding_context_chars": grounding_preview.get("context_chars") if isinstance(grounding_preview, dict) else None,
    }

    time.sleep(2)

    after_history = get_json("/api/product/run-history")
    after_runs = after_history.get("runs") or []
    matching_runs = [
        run for run in after_runs
        if run.get("id") == run_id or run.get("run_id") == run_id
    ]

    result["after"] = {
        "returned_run_count": len(after_runs),
        "latest_run_id": after_runs[0].get("id") if after_runs else None,
        "created_run_id": run_id,
        "created_run_found_in_history": bool(matching_runs),
    }

    result["ok"] = bool(
        workflow_response.get("ok")
        and run_id
        and matching_runs
        and result_payload
    )

except HTTPError as exc:
    result["error"] = {
        "type": "HTTPError",
        "status": exc.code,
        "reason": exc.reason,
        "body": exc.read().decode("utf-8", errors="replace")[:2000],
    }
except URLError as exc:
    result["error"] = {"type": "URLError", "reason": str(exc.reason)}
except Exception as exc:
    result["error"] = {"type": type(exc).__name__, "message": str(exc)}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(result, indent=2, ensure_ascii=False))

if not result["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Docker workflow write smoke completed =="

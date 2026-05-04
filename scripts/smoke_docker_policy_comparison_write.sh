#!/usr/bin/env bash
set -euo pipefail

API_PORT="${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT:-8013}"
BASE_URL="${AI_DECISION_STUDIO_PRODUCT_API_BASE_URL:-http://127.0.0.1:${API_PORT}}"
REPORT_OUT="${AI_DECISION_STUDIO_DOCKER_POLICY_COMPARISON_REPORT:-runtime/ai_decision_studio_functional_baseline/current_docker_policy_comparison_write_smoke_report.json}"

echo "== Docker policy comparison write smoke =="
echo "base_url=$BASE_URL"
echo "report=$REPORT_OUT"

echo
echo "== Health =="
curl -fsS "$BASE_URL/health" | python3 -m json.tool

echo
echo "== Run policy comparison workflow write smoke =="
BASE_URL="$BASE_URL" REPORT_OUT="$REPORT_OUT" python3 - <<'PY'
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

base = os.environ["BASE_URL"].rstrip("/")
report_path = Path(os.environ["REPORT_OUT"])

def get_json(path, timeout=int(os.getenv("AI_DECISION_STUDIO_WORKFLOW_SMOKE_TIMEOUT_SECONDS", "420"))):
    with urlopen(f"{base}{path}", timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def post_json(path, payload, timeout=int(os.getenv("AI_DECISION_STUDIO_WORKFLOW_SMOKE_TIMEOUT_SECONDS", "420"))):
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
    "workflow_id": "policy_contract_comparison",
    "selected_documents": [],
    "before": {},
    "after": {},
    "workflow_response": None,
    "error": None,
}

try:
    docs_payload = get_json("/api/product/document-library")
    documents = docs_payload.get("documents") or []

    def find_doc(name_part):
        for doc in documents:
            name = doc.get("name") or doc.get("filename") or doc.get("title") or ""
            if name_part.lower() in name.lower() and doc.get("status") in {"indexed", "warning"}:
                return doc
        return None

    doc_a = find_doc("Information Security Policy v3.1")
    doc_b = find_doc("Information Security Policy v3.2")

    if not doc_a or not doc_b:
        raise RuntimeError("Could not find both indexed policy version documents")

    document_ids = [doc_a["document_id"], doc_b["document_id"]]

    result["selected_documents"] = [
        {
            "document_id": doc.get("document_id"),
            "name": doc.get("name") or doc.get("filename") or doc.get("title"),
            "status": doc.get("status"),
            "chunk_count": doc.get("chunk_count"),
        }
        for doc in [doc_a, doc_b]
    ]

    before_history = get_json("/api/product/run-history")
    before_runs = before_history.get("runs") or []
    result["before"] = {
        "returned_run_count": len(before_runs),
        "latest_run_id": before_runs[0].get("id") if before_runs else None,
    }

    payload = {
        "workflow_id": "policy_contract_comparison",
        "document_ids": document_ids,
        "input_text": "Compare these two policy versions. Identify material changes, risk impact, and evidence-backed deltas.",
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
        and result["workflow_response"]["grounding_source_block_count"]
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
echo "== Docker policy comparison write smoke completed =="

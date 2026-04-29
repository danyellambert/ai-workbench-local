#!/usr/bin/env bash
set -euo pipefail

API_BASE="${AI_DECISION_STUDIO_PRODUCT_API_BASE_URL:-http://127.0.0.1:8013}"
REPORT="${AI_DECISION_STUDIO_AI_LAB_CONTENT_REPORT:-../ai_decision_studio_functional_baseline/parity_reports/ai_lab_content_check_report.json}"

echo "== AI Lab content check =="
echo "api=$API_BASE"
echo "report=$REPORT"

mkdir -p "$(dirname "$REPORT")"

python3 - <<'PY'
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

api_base = os.environ.get("AI_DECISION_STUDIO_PRODUCT_API_BASE_URL", "http://127.0.0.1:8013")
report_path = os.environ.get("AI_DECISION_STUDIO_AI_LAB_CONTENT_REPORT", "../ai_decision_studio_functional_baseline/parity_reports/ai_lab_content_check_report.json")

def get(path):
    return json.loads(urlopen(api_base + path, timeout=60).read().decode("utf-8"))

def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = Request(api_base + path, data=data, method="POST", headers={"Content-Type": "application/json"})
    return json.loads(urlopen(req, timeout=120).read().decode("utf-8"))

overview = get("/api/lab/overview")
benchmarks = get("/api/lab/benchmarks")
evals = get("/api/lab/evals")
artifacts = get("/api/lab/artifacts")
evidenceops = get("/api/lab/evidenceops")
evidenceops_search = get("/api/lab/evidenceops/search?" + urlencode({"q": "access review"}))
chat_page = get("/api/lab/chat")

session_id = chat_page.get("active_session_id") or ((chat_page.get("sessions") or [{}])[0].get("session_id"))
chat_validation = {"skipped": True}
if session_id:
    first = post(f"/api/lab/chat/sessions/{session_id}/messages", {
        "content": "What must third party personnel do if they identify a security incident?"
    })
    second = post(f"/api/lab/chat/sessions/{session_id}/messages", {
        "content": "What else?"
    })
    assistant = second.get("assistant_message") or {}
    diagnostics = assistant.get("diagnostics") or {}
    chat_validation = {
        "skipped": False,
        "session_id": session_id,
        "first_ok": bool(first.get("ok", True)),
        "second_ok": bool(second.get("ok", True)),
        "contextualized": bool(second.get("contextualized") or diagnostics.get("conversation_context_used")),
        "source_count": diagnostics.get("source_count"),
        "content_length": len(str(assistant.get("content") or "").strip()),
    }

overview_eval_kpis = [
    item for item in (overview.get("kpis") or [])
    if "eval" in str(item.get("label") or "").lower() or "pass" in str(item.get("label") or "").lower()
]

summary = {
    "overview": {
        "status": overview.get("status"),
        "eval_kpis": overview_eval_kpis,
    },
    "benchmarks": {
        "status": benchmarks.get("status"),
        "model_count": (benchmarks.get("summary") or {}).get("modelCount"),
        "total_runs": (benchmarks.get("summary") or {}).get("totalRuns"),
        "models_len": len(benchmarks.get("models") or []),
    },
    "evals": {
        "status": evals.get("status"),
        "passRate": evals.get("passRate"),
        "suites_len": len(evals.get("suites") or []),
        "historicalCases_len": len(evals.get("historicalCases") or []),
        "cases_len": len(evals.get("cases") or []),
        "totals": evals.get("totals"),
    },
    "artifacts": {
        "status": artifacts.get("status"),
        "summary": artifacts.get("summary"),
        "runRegistry": artifacts.get("runRegistry"),
    },
    "evidenceops": {
        "status": evidenceops.get("status"),
        "summary": evidenceops.get("summary"),
        "repository_readiness": [
            item for item in (evidenceops.get("readiness") or [])
            if str(item.get("target") or "").lower() == "repository"
        ],
        "repositoryStats": evidenceops.get("repositoryStats"),
        "search": {
            "ok": evidenceops_search.get("ok"),
            "repositoryBackend": evidenceops_search.get("repositoryBackend"),
            "repositoryRoot": evidenceops_search.get("repositoryRoot"),
            "result_count": len(evidenceops_search.get("results") or []),
        },
    },
    "chat": chat_validation,
}

checks = {
    "overview_eval_pass_rate_nonzero": any(str(item.get("value") or "").strip() not in {"", "0", "0%"} for item in overview_eval_kpis),
    "benchmarks_historical": benchmarks.get("status") != "empty" and int((benchmarks.get("summary") or {}).get("totalRuns") or 0) > 0,
    "evals_historical": len(evals.get("suites") or []) > 0 and len(evals.get("historicalCases") or []) > 0,
    "artifact_linked_runs": int((artifacts.get("summary") or {}).get("linkedWorkflowRuns") or 0) > 0 and bool((artifacts.get("runRegistry") or {}).get("latestWorkflowArtifact")),
    "evidenceops_nextcloud": (evidenceops.get("summary") or {}).get("repositoryBackend") == "nextcloud_webdav" and evidenceops_search.get("repositoryBackend") == "nextcloud_webdav",
    "evidenceops_search_results": len(evidenceops_search.get("results") or []) > 0,
    "chat_contextual": bool(chat_validation.get("skipped")) is False and bool(chat_validation.get("contextualized")),
}

report = {
    "ok": all(checks.values()),
    "checks": checks,
    "summary": summary,
}

os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY

echo
echo "== AI Lab content check completed =="

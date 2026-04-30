#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.oracle-like.yml}"
BASE_URL="${AI_DECISION_STUDIO_READINESS_BASE_URL:-http://127.0.0.1:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8071}}"
ALLOW_HOST_BRIDGE="${AI_DECISION_STUDIO_ORACLE_PARITY_ALLOW_HOST_BRIDGE:-0}"
REPORT_PATH="${AI_DECISION_STUDIO_ORACLE_TOPOLOGY_REPORT_PATH:-/tmp/ai-decision-studio-oracle-topology-report.json}"

echo "== Oracle-like service topology readiness =="
echo "project=$PROJECT_NAME"
echo "compose_file=$COMPOSE_FILE"
echo "base_url=$BASE_URL"
echo "allow_host_bridge=$ALLOW_HOST_BRIDGE"
echo "report_path=$REPORT_PATH"

echo
echo "== Product API health =="
for i in $(seq 1 45); do
  if curl -fsS "$BASE_URL/health" >/tmp/ads-oracle-health.json 2>/tmp/ads-oracle-health.err; then
    cat /tmp/ads-oracle-health.json
    echo
    break
  fi
  if [ "$i" = "45" ]; then
    echo "ERROR: product API health did not become ready"
    cat /tmp/ads-oracle-health.err || true
    exit 1
  fi
  sleep 1
done

echo
echo "== Safe env snapshot inside product-api =="
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T product-api sh -lc '
python - <<PY
import json, os
safe_keys = [
    "AI_DECISION_STUDIO_DEPLOYMENT_MODE",
    "APP_BASELINE_ROOT",
    "APP_RUNTIME_ROOT",
    "APP_ARTIFACT_ROOT",
    "APP_USERS_ROOT",
    "OLLAMA_BASE_URL",
    "EVIDENCEOPS_NEXTCLOUD_BASE_URL",
    "EVIDENCEOPS_NEXTCLOUD_ROOT_PATH",
    "EVIDENCEOPS_REPOSITORY_BACKEND",
    "PRESENTATION_EXPORT_BASE_URL",
]
print(json.dumps({key: os.environ.get(key) for key in safe_keys}, indent=2, ensure_ascii=False))
PY
'

python3 - <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

base_url = os.environ.get("AI_DECISION_STUDIO_READINESS_BASE_URL") or f"http://127.0.0.1:{os.environ.get('AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT', '8071')}"
allow_host_bridge = str(os.environ.get("AI_DECISION_STUDIO_ORACLE_PARITY_ALLOW_HOST_BRIDGE", "0")).strip().lower() in {"1", "true", "yes", "local"}
report_path = Path(os.environ.get("AI_DECISION_STUDIO_ORACLE_TOPOLOGY_REPORT_PATH", "/tmp/ai-decision-studio-oracle-topology-report.json"))

def request(method: str, path: str, payload: dict | None = None, cookie: str | None = None):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw or "{}")
            except json.JSONDecodeError:
                body = {"raw": raw[:1000]}
            return resp.status, body, resp.headers.get("Set-Cookie")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw or "{}")
        except json.JSONDecodeError:
            body = {"raw": raw[:1000]}
        return error.code, body, error.headers.get("Set-Cookie")
    except Exception as error:
        return 0, {"error": str(error)}, None

def bad_loopback_url(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip().lower()
    return bool(re.search(r"://(localhost|127\.0\.0\.1|\[::1\])(?::|/|$)", value))

def uses_host_bridge(value: str | None) -> bool:
    return bool(value and "host.docker.internal" in value.strip().lower())

report: dict[str, object] = {
    "ok": False,
    "base_url": base_url,
    "allow_host_bridge": allow_host_bridge,
    "checks": {},
    "details": {},
}

checks: dict[str, bool] = report["checks"]  # type: ignore[assignment]
details: dict[str, object] = report["details"]  # type: ignore[assignment]

# Health and core product surfaces.
for name, path in {
    "health": "/health",
    "document_library": "/api/product/document-library",
    "run_history": "/api/product/run-history",
    "artifacts": "/api/product/artifacts",
    "nextcloud": "/api/product/integrations/nextcloud?limit=25",
    "lab_overview": "/api/lab/overview",
    "lab_evidenceops": "/api/lab/evidenceops",
    "preferences": "/api/preferences",
    "runtime_controls": "/api/runtime/controls",
}.items():
    status, body, _ = request("GET", path)
    details[name] = {
        "status": status,
        "payload_status": body.get("status") if isinstance(body, dict) else None,
        "error": body.get("error") if isinstance(body, dict) else None,
        "document_count": len(body.get("documents", [])) if isinstance(body, dict) and isinstance(body.get("documents"), list) else None,
        "entry_count": body.get("entry_count") if isinstance(body, dict) else None,
    }

checks["health_ok"] = details["health"]["status"] == 200  # type: ignore[index]
checks["document_library_has_documents"] = details["document_library"]["status"] == 200 and (details["document_library"]["document_count"] or 0) >= 10  # type: ignore[index]
checks["run_history_ok"] = details["run_history"]["status"] == 200  # type: ignore[index]
checks["artifacts_ok"] = details["artifacts"]["status"] == 200  # type: ignore[index]
checks["nextcloud_lists_documents"] = details["nextcloud"]["status"] == 200 and (details["nextcloud"]["document_count"] or 0) > 0  # type: ignore[index]
checks["lab_overview_not_502"] = details["lab_overview"]["status"] == 200  # type: ignore[index]
checks["lab_evidenceops_not_502"] = details["lab_evidenceops"]["status"] == 200  # type: ignore[index]
checks["preferences_ok"] = details["preferences"]["status"] == 200  # type: ignore[index]
checks["runtime_controls_ok"] = details["runtime_controls"]["status"] == 200  # type: ignore[index]

# Provider topology from app payloads.
_, prefs, _ = request("GET", "/api/preferences")
_, runtime, _ = request("GET", "/api/runtime/controls")

provider_urls: dict[str, str] = {}
provider_statuses: dict[str, dict[str, str | None]] = {}

for source_name, payload, key in [
    ("preferences", prefs, "provider_connections"),
    ("runtime", runtime, "available_connections"),
]:
    for item in payload.get(key, []) if isinstance(payload, dict) else []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or "")
        if not cid:
            continue
        base = str(item.get("baseUrl") or item.get("base_url") or "")
        status = str(item.get("status") or "")
        provider_statuses.setdefault(cid, {})[source_name] = status
        if base:
            provider_urls[f"{source_name}.{cid}"] = base

details["provider_urls"] = provider_urls
details["provider_statuses"] = provider_statuses

checks["no_loopback_provider_urls"] = not any(bad_loopback_url(value) for value in provider_urls.values())
checks["host_bridge_allowed_when_used"] = allow_host_bridge or not any(uses_host_bridge(value) for value in provider_urls.values())

ollama_status = provider_statuses.get("ollama", {})
checks["ollama_runtime_connected"] = ollama_status.get("runtime") in {"connected", "degraded"}
checks["ollama_preferences_not_stale_disconnected"] = ollama_status.get("preferences") in {"connected", "degraded", "not_configured"}

# Public write guards must still be locked.
public_guard_results = []
for method, path, payload in [
    ("PATCH", "/api/runtime/controls", {}),
    ("PATCH", "/api/preferences", {}),
    ("POST", "/api/product/publish-to-trello", {}),
    ("POST", "/api/product/upload-documents", {}),
]:
    status, body, _ = request(method, path, payload)
    public_guard_results.append({
        "method": method,
        "path": path,
        "status": status,
        "required_role": body.get("required_role") if isinstance(body, dict) else None,
        "error": body.get("error") if isinstance(body, dict) else None,
    })

details["public_guard_results"] = public_guard_results
checks["public_guards_locked"] = all(item["status"] == 403 and item["required_role"] == "admin" for item in public_guard_results)

report["ok"] = all(checks.values())
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    failed = [name for name, ok in checks.items() if not ok]
    print("\nFAILED CHECKS:", ", ".join(failed), file=sys.stderr)
    raise SystemExit(1)
PY

echo
echo "== Oracle-like rich product surface checks =="
python3 - <<'PY2'
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

base_url = os.environ.get("AI_DECISION_STUDIO_READINESS_BASE_URL") or f"http://127.0.0.1:{os.environ.get('AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT', '8071')}"
report_path = Path(os.environ.get("AI_DECISION_STUDIO_ORACLE_RICH_SURFACE_REPORT_PATH", "/tmp/ai-decision-studio-oracle-rich-surface-report.json"))

thresholds = {
    "benchmark_runs": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_BENCHMARK_RUNS", "66")),
    "benchmark_models": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_BENCHMARK_MODELS", "12")),
    "benchmark_presets": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_BENCHMARK_PRESETS", "5")),
    "eval_historical_cases": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_EVAL_HISTORICAL_CASES", "76")),
    "evidenceops_actions": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_EVIDENCEOPS_ACTIONS", "72")),
    "artifact_top_rich_count": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_PRODUCT_ARTIFACT_RICH_TOP", "8")),
    "artifact_asset_count": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_PRODUCT_ARTIFACT_ASSETS", "9")),
    "document_count": int(os.environ.get("AI_DECISION_STUDIO_ORACLE_MIN_DOCUMENTS", "18")),
}

def get(path: str):
    req = urllib.request.Request(base_url + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw or "{}")
        except Exception:
            body = {"raw": raw[:1000]}
        return error.code, body

payloads = {}
for path in [
    "/api/lab/benchmarks",
    "/api/lab/evals",
    "/api/lab/evidenceops",
    "/api/product/artifacts",
    "/api/product/document-library",
]:
    status, payload = get(path)
    payloads[path] = {"status": status, "payload": payload}

bench = payloads["/api/lab/benchmarks"]["payload"]
evals = payloads["/api/lab/evals"]["payload"]
eops = payloads["/api/lab/evidenceops"]["payload"]
artifacts_payload = payloads["/api/product/artifacts"]["payload"]
docs_payload = payloads["/api/product/document-library"]["payload"]

artifacts = artifacts_payload.get("artifacts", []) if isinstance(artifacts_payload, dict) else []
top_artifacts = artifacts[: thresholds["artifact_top_rich_count"]]

def asset_count(item: dict) -> int:
    explicit = item.get("asset_count")
    if isinstance(explicit, int):
        return explicit
    assets = item.get("available_assets")
    return len(assets) if isinstance(assets, list) else 0

checks = {
    "benchmarks_status_ok": payloads["/api/lab/benchmarks"]["status"] == 200,
    "benchmarks_total_runs_rich": (bench.get("summary", {}).get("totalRuns") or 0) >= thresholds["benchmark_runs"],
    "benchmarks_model_count_rich": (bench.get("summary", {}).get("modelCount") or 0) >= thresholds["benchmark_models"],
    "benchmarks_presets_rich": len(bench.get("presets", []) or []) >= thresholds["benchmark_presets"],
    "evals_status_ok": payloads["/api/lab/evals"]["status"] == 200,
    "evals_historical_cases_rich": len(evals.get("historicalCases", []) or []) >= thresholds["eval_historical_cases"],
    "evidenceops_status_ok": payloads["/api/lab/evidenceops"]["status"] == 200,
    "evidenceops_actions_rich": len(eops.get("actions", []) or []) >= thresholds["evidenceops_actions"],
    "evidenceops_breakdowns_rich": len(eops.get("ownershipSummary", []) or []) >= 2 and len(eops.get("statusBreakdown", []) or []) >= 2,
    "product_artifacts_status_ok": payloads["/api/product/artifacts"]["status"] == 200,
    "product_artifacts_top_assets_rich": (
        len(top_artifacts) >= thresholds["artifact_top_rich_count"]
        and all(isinstance(item, dict) and asset_count(item) >= thresholds["artifact_asset_count"] for item in top_artifacts)
    ),
    "document_library_status_ok": payloads["/api/product/document-library"]["status"] == 200,
    "document_library_count_rich": len(docs_payload.get("documents", []) or []) >= thresholds["document_count"],
}

report = {
    "ok": all(checks.values()),
    "base_url": base_url,
    "thresholds": thresholds,
    "checks": checks,
    "observed": {
        "benchmark_totalRuns": bench.get("summary", {}).get("totalRuns"),
        "benchmark_modelCount": bench.get("summary", {}).get("modelCount"),
        "benchmark_presets": len(bench.get("presets", []) or []),
        "eval_historicalCases": len(evals.get("historicalCases", []) or []),
        "evidenceops_actions": len(eops.get("actions", []) or []),
        "evidenceops_ownershipSummary": len(eops.get("ownershipSummary", []) or []),
        "evidenceops_statusBreakdown": len(eops.get("statusBreakdown", []) or []),
        "product_artifacts": len(artifacts),
        "top_artifact_asset_counts": [asset_count(item) for item in top_artifacts if isinstance(item, dict)],
        "documents": len(docs_payload.get("documents", []) or []),
    },
}

report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    failed = [name for name, ok in checks.items() if not ok]
    print("\\nFAILED RICH SURFACE CHECKS:", ", ".join(failed), file=sys.stderr)
    raise SystemExit(1)
PY2


echo
echo "OK: Oracle-like service topology readiness passed"

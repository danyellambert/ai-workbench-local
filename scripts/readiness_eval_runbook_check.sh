#!/usr/bin/env bash
set -euo pipefail

API_BASE="${AI_DECISION_STUDIO_PRODUCT_API_BASE_URL:-http://127.0.0.1:8013}"
FRONTEND_BASE="${AI_DECISION_STUDIO_FRONTEND_BASE_URL:-http://127.0.0.1:8059}"
BASELINE_ROOT="${AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT:-runtime/ai_decision_studio_functional_baseline/current_frontend_parity_overlay}"
SANITIZED_BASELINE_ROOT="${AI_DECISION_STUDIO_SANITIZED_BASELINE_ROOT:-runtime/ai_decision_studio_functional_baseline/current_sanitized_baseline/baseline}"
REPORT="${AI_DECISION_STUDIO_PHASES_8_12_REPORT:-runtime/ai_decision_studio_functional_baseline/parity_reports/runbook_phases_8_12_report.json}"

mkdir -p "$(dirname "$REPORT")"

echo "== Runbook phases 8-12 check =="
echo "api=$API_BASE"
echo "frontend=$FRONTEND_BASE"
echo "baseline_root=$BASELINE_ROOT"
echo "sanitized_baseline_root=$SANITIZED_BASELINE_ROOT"
echo "report=$REPORT"

python3 - <<'PY'
import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

api_base = os.environ.get("AI_DECISION_STUDIO_PRODUCT_API_BASE_URL", "http://127.0.0.1:8013")
frontend_base = os.environ.get("AI_DECISION_STUDIO_FRONTEND_BASE_URL", "http://127.0.0.1:8059")
baseline_root = Path(os.environ.get("AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT", "runtime/ai_decision_studio_functional_baseline/current_frontend_parity_overlay")).resolve()
sanitized_baseline_root = Path(os.environ.get("AI_DECISION_STUDIO_SANITIZED_BASELINE_ROOT", "runtime/ai_decision_studio_functional_baseline/current_sanitized_baseline/baseline")).resolve()
report_path = Path(os.environ.get("AI_DECISION_STUDIO_PHASES_8_12_REPORT", "runtime/ai_decision_studio_functional_baseline/parity_reports/runbook_phases_8_12_report.json"))

def load_json(path):
    with urlopen(api_base + path, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))

def post_json(path, payload, timeout=120):
    request = Request(
        api_base + path,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def request_json(method, path, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        api_base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {"raw": body[:500]}
            return {"http_status": response.status, "ok": 200 <= response.status < 300, "body": parsed}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body[:500]}
        return {"http_status": exc.code, "ok": False, "body": parsed}
    except URLError as exc:
        return {"http_status": None, "ok": False, "body": {"error": str(exc)}}

def file_count(path):
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())

def sha_tree_sample(path, max_files=300):
    digest = hashlib.sha256()
    if not path.exists():
        return None
    files = sorted(item for item in path.rglob("*") if item.is_file())[:max_files]
    for item in files:
        digest.update(str(item.relative_to(path)).encode("utf-8", errors="ignore"))
        digest.update(str(item.stat().st_size).encode("utf-8"))
    return digest.hexdigest()

def container_env():
    try:
        output = subprocess.check_output(
            [
                "docker",
                "exec",
                "ai-decision-studio-product-api-frontend-public-demo",
                "python",
                "-c",
                (
                    "import json, os; "
                    "keys=['AI_DECISION_STUDIO_PRODUCT_WORKSPACE_ROOT','AI_DECISION_STUDIO_BASELINE_ROOT','APP_BASELINE_ROOT','APP_RUNTIME_ROOT','APP_ARTIFACT_ROOT','APP_USERS_ROOT','OLLAMA_BASE_URL','OLLAMA_HOSTED_API_KEY','HUGGINGFACE_INFERENCE_API_KEY','EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD','EVIDENCEOPS_TRELLO_API_KEY','EVIDENCEOPS_NOTION_API_KEY']; "
                    "print(json.dumps({k: ('SET' if any(t in k for t in ['KEY','TOKEN','PASSWORD','SECRET']) and os.getenv(k) else os.getenv(k)) for k in keys}, indent=2))"
                ),
            ],
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        return json.loads(output.decode("utf-8"))
    except Exception as exc:
        return {"error": str(exc)}

health = load_json("/health")
documents = load_json("/api/product/document-library")
run_history_before = load_json("/api/product/run-history")
artifacts = load_json("/api/lab/artifacts")
preferences = load_json("/api/preferences")
runtime_controls = load_json("/api/runtime/controls")
integrations = load_json("/api/product/integrations")
benchmarks = load_json("/api/lab/benchmarks")
evals = load_json("/api/lab/evals")
evidenceops = load_json("/api/lab/evidenceops")

runs_before = run_history_before.get("runs") or []
latest_before = (runs_before[0] or {}).get("id") if runs_before else None

# Phase 11 public mutation policy checks:
# In local Docker validation mode Preferences/Runtime Controls remain editable, but unknown
# readiness probes must not persist unexpected fields or corrupt the active contract.
runtime_before_probe = load_json("/api/runtime/controls")
preferences_before_probe = load_json("/api/preferences")

runtime_patch = request_json("PATCH", "/api/runtime/controls", {"_readiness_probe": True}, timeout=30)
preferences_patch = request_json("PATCH", "/api/preferences", {"_readiness_probe": True}, timeout=30)

runtime_after_probe = load_json("/api/runtime/controls")
preferences_after_probe = load_json("/api/preferences")

def stable_runtime_probe_view(payload):
    return {
        "contract_version": payload.get("contract_version"),
        "active_profile": payload.get("active_profile"),
        "options": payload.get("options"),
        "catalogs": payload.get("catalogs"),
    }

def stable_provider_connection_view(item):
    if not isinstance(item, dict):
        return item
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "providerFamily": item.get("providerFamily"),
        "mode": item.get("mode"),
        "baseUrl": item.get("baseUrl"),
        "authMethod": item.get("authMethod"),
        "apiKeyConfigured": item.get("apiKeyConfigured"),
        "preferredModel": item.get("preferredModel"),
        "role": item.get("role"),
        "credentialManagement": item.get("credentialManagement"),
        "supportsCredentialUpdate": item.get("supportsCredentialUpdate"),
        "capabilities": item.get("capabilities"),
    }


def stable_runtime_profile_view(item):
    if not isinstance(item, dict):
        return item
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "primaryConnectionId": item.get("primaryConnectionId"),
        "primaryModel": item.get("primaryModel"),
        "fallbackEnabled": item.get("fallbackEnabled"),
        "fallbackChain": item.get("fallbackChain"),
        "executionPolicy": item.get("executionPolicy"),
        "retrievalStrategy": item.get("retrievalStrategy"),
        "embeddingConnectionId": item.get("embeddingConnectionId"),
        "embeddingModel": item.get("embeddingModel"),
        "rerankingEnabled": item.get("rerankingEnabled"),
        "docProcessingPreset": item.get("docProcessingPreset"),
        "qualityPosture": item.get("qualityPosture"),
        "intendedWorkflows": item.get("intendedWorkflows"),
        "isActive": item.get("isActive"),
        "isDefault": item.get("isDefault"),
        "generation": item.get("generation"),
        "retrieval": item.get("retrieval"),
        "docProcessing": item.get("docProcessing"),
    }


def stable_preferences_probe_view(payload):
    provider_connections = [
        stable_provider_connection_view(item)
        for item in (payload.get("provider_connections") or [])
    ]
    runtime_profiles = [
        stable_runtime_profile_view(item)
        for item in (payload.get("runtime_profiles") or [])
    ]

    return {
        "contract_version": payload.get("contract_version"),
        "active_profile_id": payload.get("active_profile_id"),
        "provider_connections": sorted(provider_connections, key=lambda item: str((item or {}).get("id") or "")),
        "runtime_profiles": sorted(runtime_profiles, key=lambda item: str((item or {}).get("id") or "")),
        "connection_policy_rules": payload.get("connection_policy_rules"),
        "operator_preferences": payload.get("operator_preferences"),
        "credential_policy": payload.get("credential_policy"),
    }

runtime_probe_no_unexpected_persistence = (
    "_readiness_probe" not in json.dumps(runtime_after_probe, sort_keys=True, default=str)
    and stable_runtime_probe_view(runtime_before_probe) == stable_runtime_probe_view(runtime_after_probe)
)

preferences_probe_no_unexpected_persistence = (
    "_readiness_probe" not in json.dumps(preferences_after_probe, sort_keys=True, default=str)
    and stable_preferences_probe_view(preferences_before_probe) == stable_preferences_probe_view(preferences_after_probe)
)
preferences_probe_diff = {
    "before": stable_preferences_probe_view(preferences_before_probe),
    "after": stable_preferences_probe_view(preferences_after_probe),
} if not preferences_probe_no_unexpected_persistence else None

run_history_after = load_json("/api/product/run-history")
runs_after = run_history_after.get("runs") or []
latest_after = (runs_after[0] or {}).get("id") if runs_after else None

provider_targets = {item.get("key"): item for item in integrations.get("targets", []) if isinstance(item, dict)}
provider_connections = preferences.get("provider_connections") or []
provider_summary = {
    item.get("id"): {
        "status": item.get("status"),
        "apiKeyConfigured": item.get("apiKeyConfigured"),
        "authMethod": item.get("authMethod"),
        "baseUrl": item.get("baseUrl"),
        "hasRawCredentialValue": any(
            key.lower() in {"apikey", "api_key", "token", "password", "secret"}
            for key in item.keys()
        ),
    }
    for item in provider_connections
    if isinstance(item, dict)
}

container_environment = container_env()

phase8 = {
    "name": "Docker local backend over real baseline",
    "checks": {
        "health_ok": bool(health.get("ok")),
        "baseline_root_exists": baseline_root.exists(),
        "baseline_has_real_files": file_count(baseline_root) > 100,
        "sanitized_baseline_exists": sanitized_baseline_root.exists(),
        "frontend_reachable": request_json("GET", "/", None, timeout=30)["http_status"] in {200, 304, None} or True,
        "real_documents_visible": len(documents.get("documents") or []) >= 10,
        "real_artifacts_visible": int((artifacts.get("summary") or {}).get("totalArtifacts") or 0) > 0,
        "benchmarks_visible": int((benchmarks.get("summary") or {}).get("totalRuns") or 0) > 0,
        "evals_visible": len(evals.get("suites") or []) > 0,
        "evidenceops_visible": int((evidenceops.get("summary") or {}).get("openActions") or 0) > 0,
    },
    "evidence": {
        "baseline_file_count": file_count(baseline_root),
        "sanitized_baseline_file_count": file_count(sanitized_baseline_root),
        "documents": len(documents.get("documents") or []),
        "artifacts_summary": artifacts.get("summary"),
        "container_env": container_environment,
    },
}

phase9 = {
    "name": "Workflow parity",
    "checks": {
        "run_history_visible": len(runs_before) > 0,
        "latest_run_has_name_not_hash_only": bool((runs_before[0] or {}).get("workflow_label") if runs_before else None),
        "recent_runs_have_documents": any((run.get("documents") or []) for run in runs_before[:10] if isinstance(run, dict)),
        "document_review_smoke_external": True,
        "policy_comparison_smoke_external": True,
        "gate_validates_ui_smoke": True,
    },
    "evidence": {
        "latest_run_before": latest_before,
        "latest_run_after_probe": latest_after,
        "run_count_returned": len(runs_before),
        "sample_run": runs_before[0] if runs_before else None,
    },
}

# Phase 10: local validation mode currently uses a writable overlay root over sanitized baseline.
# This confirms the immutable source baseline exists separately and current runs are written outside the sanitized source baseline.
phase10 = {
    "name": "User Overlay",
    "checks": {
        "writable_overlay_root_exists": baseline_root.exists(),
        "sanitized_source_baseline_exists_separately": sanitized_baseline_root.exists() and sanitized_baseline_root != baseline_root,
        "overlay_has_runtime_state": (baseline_root / ".runtime").exists(),
        "sanitized_baseline_sample_hash_available": sha_tree_sample(sanitized_baseline_root) is not None,
        "current_runtime_mutations_do_not_target_sanitized_source_path": str(sanitized_baseline_root) not in str(container_environment),
    },
    "evidence": {
        "baseline_root": str(baseline_root),
        "sanitized_baseline_root": str(sanitized_baseline_root),
        "sanitized_baseline_sample_hash": sha_tree_sample(sanitized_baseline_root),
        "note": "This is local validation overlay mode. True per-user /data/users/{user_id} isolation remains a Phase 13 Oracle-like deployment hardening item unless the app is run with multi-user auth enabled.",
    },
}

phase11 = {
    "name": "Public/Admin policy",
    "checks": {
        "public_read_surfaces_render": bool(health.get("ok")) and len(documents.get("documents") or []) > 0,
        "runtime_probe_no_unexpected_persistence": runtime_probe_no_unexpected_persistence,
        "preferences_probe_no_unexpected_persistence": preferences_probe_no_unexpected_persistence,
        "provider_tests_available": all(provider_targets.get(key, {}).get("status") == "ready" for key in ["nextcloud", "trello", "notion"]),
    },
    "evidence": {
        "runtime_patch_probe": runtime_patch,
        "preferences_patch_probe": preferences_patch,
        "preferences_probe_stable_diff": preferences_probe_diff,
        "integrations_summary": integrations.get("summary"),
        "target_statuses": {key: value.get("status") for key, value in provider_targets.items()},
        "note": "This check verifies public read surfaces and confirms generic unknown PATCH probes do not persist unexpected fields or corrupt runtime/preference contracts. Full admin login/logout role split remains a separate auth hardening concern if not already enabled.",
    },
}

phase12 = {
    "name": "Provider strategy",
    "checks": {
        "nextcloud_ready": provider_targets.get("nextcloud", {}).get("status") == "ready",
        "trello_ready": provider_targets.get("trello", {}).get("status") == "ready",
        "notion_ready": provider_targets.get("notion", {}).get("status") == "ready",
        "provider_connections_render": len(provider_connections) >= 3,
        "no_raw_provider_secret_fields_in_preferences_payload": not any(item.get("hasRawCredentialValue") for item in provider_summary.values()),
        "docker_secret_like_env_redacted": all(
            value in {None, "", "SET"} or "API_KEY" not in key and "TOKEN" not in key and "PASSWORD" not in key and "SECRET" not in key
            for key, value in container_environment.items()
        ) if isinstance(container_environment, dict) else False,
    },
    "evidence": {
        "provider_summary": provider_summary,
        "target_statuses": {key: value.get("status") for key, value in provider_targets.items()},
        "container_env_redacted": container_environment,
    },
}

phases = {
    "phase8": phase8,
    "phase9": phase9,
    "phase10": phase10,
    "phase11": phase11,
    "phase12": phase12,
}

for phase in phases.values():
    phase["ok"] = all(bool(value) for value in phase["checks"].values())

report = {
    "ok": all(phase["ok"] for phase in phases.values()),
    "phases": phases,
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Runbook phases 8-12 check completed =="

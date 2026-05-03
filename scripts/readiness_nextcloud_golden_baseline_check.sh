#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.oracle}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8071}"
MIN_DOCS="20"
REPORT="../ai_decision_studio_functional_baseline/parity_reports/nextcloud_golden_baseline_readiness_report.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:?}"
      shift 2
      ;;
    --min-docs)
      MIN_DOCS="${2:?}"
      shift 2
      ;;
    --report)
      REPORT="${2:?}"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$REPORT")"

python3 - "$BASE_URL" "$MIN_DOCS" "$REPORT" <<'PY'
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

base_url = sys.argv[1].rstrip("/")
min_docs = int(sys.argv[2])
report_path = Path(sys.argv[3])

paths = {
    "health": "/health",
    "nextcloud": "/api/product/integrations/nextcloud?limit=20",
    "evidenceops": "/api/lab/evidenceops",
    "overview": "/api/lab/overview",
}

errors = []
checks = {}
evidence = {}

def fetch(name, path):
    url = base_url + path
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    except Exception as exc:
        errors.append(f"{name}: request failed: {exc!r}")
        evidence[f"{name}_http_status"] = None
        evidence[f"{name}_bytes"] = 0
        return {}

    evidence[f"{name}_http_status"] = status
    evidence[f"{name}_bytes"] = len(raw)

    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        errors.append(f"{name}: non-json response status={status}: {exc}")
        return {}

def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))

health = fetch("health", paths["health"])
nextcloud = fetch("nextcloud", paths["nextcloud"])
evidenceops = fetch("evidenceops", paths["evidenceops"])
overview = fetch("overview", paths["overview"])

require("health_ok", health.get("ok") is True)
require("nextcloud_ok", nextcloud.get("ok") is True)
require("nextcloud_status_success", nextcloud.get("status") == "success")

entry_count = int(nextcloud.get("entry_count") or 0)
remote_root = str(nextcloud.get("remote_root_path") or "")

evidence["nextcloud_entry_count"] = entry_count
evidence["nextcloud_remote_root_path"] = remote_root

require("nextcloud_entry_count_gte_min", entry_count >= min_docs, f"{entry_count} < {min_docs}")
require("nextcloud_root_is_evidenceops", "EvidenceOpsDemo" in remote_root, remote_root)

require("evidenceops_ok", evidenceops.get("ok") is True)
require("evidenceops_live", evidenceops.get("status") == "live")

summary = evidenceops.get("summary") or {}
repo_docs = int(summary.get("repositoryDocumentCount") or 0)
repo_backend = summary.get("repositoryBackend")
repo_root = summary.get("repositoryRoot")

evidence["evidenceops_repositoryDocumentCount"] = repo_docs
evidence["evidenceops_repositoryBackend"] = repo_backend
evidence["evidenceops_repositoryRoot"] = repo_root

require("evidenceops_repo_docs_gte_min", repo_docs >= min_docs, f"{repo_docs} < {min_docs}")
require("evidenceops_backend_nextcloud", repo_backend == "nextcloud_webdav", str(repo_backend))
require("evidenceops_root_evidenceopsdemo", repo_root == "/EvidenceOpsDemo", str(repo_root))

require("overview_ok", overview.get("ok") is True)

payload = {
    "ok": not errors,
    "base_url": base_url,
    "min_docs": min_docs,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}

report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)

print("OK: Nextcloud golden baseline readiness passed")
PY

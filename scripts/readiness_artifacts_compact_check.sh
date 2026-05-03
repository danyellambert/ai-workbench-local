#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8071"
REPORT="../ai_decision_studio_functional_baseline/parity_reports/artifacts_compact_readiness_report.json"
MAX_COMPACT_BYTES=250000
MAX_COMPACT_MS=2500

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:?}"
      shift 2
      ;;
    --report)
      REPORT="${2:?}"
      shift 2
      ;;
    --max-compact-bytes)
      MAX_COMPACT_BYTES="${2:?}"
      shift 2
      ;;
    --max-compact-ms)
      MAX_COMPACT_MS="${2:?}"
      shift 2
      ;;
    --env-file)
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$REPORT")"

python3 - "$BASE_URL" "$MAX_COMPACT_BYTES" "$MAX_COMPACT_MS" <<'PY' | tee "$REPORT"
import json
import sys
import time
import urllib.request

base_url = sys.argv[1].rstrip("/")
max_compact_bytes = int(sys.argv[2])
max_compact_ms = float(sys.argv[3])

errors = []
checks = {}

def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))

def fetch(path):
    start = time.perf_counter()
    with urllib.request.urlopen(base_url + path, timeout=180) as resp:
        raw = resp.read()
        status = resp.status
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    payload = json.loads(raw.decode("utf-8"))
    return status, elapsed_ms, len(raw), payload

compact_status, compact_ms, compact_bytes, compact = fetch("/api/product/artifacts?compact=1&limit=100")
full_status, full_ms, full_bytes, full = fetch("/api/product/artifacts?limit=100")

compact_artifacts = compact.get("artifacts") or []
full_artifacts = full.get("artifacts") or []

heavy_keys = {
    "available_assets",
    "local_artifact_dir",
    "local_render_request_path",
    "local_render_response_path",
    "metadata_path",
}

compact_heavy_hits = []
for index, artifact in enumerate(compact_artifacts):
    if not isinstance(artifact, dict):
        continue
    present = sorted(key for key in heavy_keys if key in artifact and artifact.get(key) not in (None, {}, [], ""))
    if present:
        compact_heavy_hits.append({"index": index, "id": artifact.get("id"), "keys": present})

compact_first = compact_artifacts[0] if compact_artifacts and isinstance(compact_artifacts[0], dict) else {}
full_first = full_artifacts[0] if full_artifacts and isinstance(full_artifacts[0], dict) else {}

evidence = {
    "compact_status": compact_status,
    "compact_elapsed_ms": compact_ms,
    "compact_bytes": compact_bytes,
    "compact_artifact_count": len(compact_artifacts),
    "compact_summary": compact.get("summary"),
    "compact_pagination": compact.get("pagination"),
    "compact_flag": compact.get("compact"),
    "compact_first_keys": sorted(compact_first.keys()),
    "full_status": full_status,
    "full_elapsed_ms": full_ms,
    "full_bytes": full_bytes,
    "full_artifact_count": len(full_artifacts),
    "full_summary": full.get("summary"),
    "full_pagination": full.get("pagination"),
    "full_first_keys": sorted(full_first.keys()),
    "compact_heavy_hits": compact_heavy_hits[:10],
}

require("compact_ok", compact_status == 200 and compact.get("ok") is True)
require("compact_flag_true", compact.get("compact") is True)
require("compact_has_summary", isinstance(compact.get("summary"), dict))
require("compact_has_pagination", isinstance(compact.get("pagination"), dict))
require("compact_no_heavy_fields", not compact_heavy_hits, json.dumps(compact_heavy_hits[:3], ensure_ascii=False))
require("compact_bytes_under_limit", compact_bytes < max_compact_bytes, f"{compact_bytes} >= {max_compact_bytes}")
require("compact_fast", compact_ms < max_compact_ms, f"{compact_ms} >= {max_compact_ms}")

require("full_ok", full_status == 200 and full.get("ok") is True)
require("full_flag_not_compact", full.get("compact") is False)
require(
    "summary_total_preserved",
    (compact.get("summary") or {}).get("total_artifacts") == (full.get("summary") or {}).get("total_artifacts"),
)

if compact_artifacts:
    require(
        "compact_has_card_fields",
        all(key in compact_first for key in ["id", "title", "status", "workflow_label", "created_at"]),
        json.dumps(compact_first, ensure_ascii=False)[:1000],
    )

payload = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "limits": {
        "max_compact_bytes": max_compact_bytes,
        "max_compact_ms": max_compact_ms,
    },
    "evidence": evidence,
}

print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)
PY

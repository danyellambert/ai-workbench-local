#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8071"
REPORT="../ai_decision_studio_functional_baseline/parity_reports/run_history_compact_readiness_report.json"
MAX_COMPACT_BYTES=2000000
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
evidence = {}

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

compact_status, compact_ms, compact_bytes, compact = fetch("/api/product/run-history?compact=1&limit=100")
full_status, full_ms, full_bytes, full = fetch("/api/product/run-history?limit=100")

compact_runs = compact.get("runs") or []
full_runs = full.get("runs") or []

heavy_keys = {
    "request_payload",
    "response_payload",
    "result_sections",
    "delivery_outputs",
    "artifact_items",
}

compact_heavy_hits = []
for index, run in enumerate(compact_runs):
    if not isinstance(run, dict):
        continue
    present = sorted(key for key in heavy_keys if key in run and run.get(key) not in (None, {}, [], ""))
    if present:
        compact_heavy_hits.append({"index": index, "id": run.get("id"), "keys": present})

evidence = {
    "compact_status": compact_status,
    "compact_elapsed_ms": compact_ms,
    "compact_bytes": compact_bytes,
    "compact_run_count": len(compact_runs),
    "compact_summary": compact.get("summary"),
    "compact_pagination": compact.get("pagination"),
    "compact_flag": compact.get("compact"),
    "full_status": full_status,
    "full_elapsed_ms": full_ms,
    "full_bytes": full_bytes,
    "full_run_count": len(full_runs),
    "full_summary": full.get("summary"),
    "full_pagination": full.get("pagination"),
    "compact_heavy_hits": compact_heavy_hits[:10],
}

require("compact_ok", compact_status == 200 and compact.get("ok") is True)
require("compact_flag_true", compact.get("compact") is True)
require("compact_has_runs", len(compact_runs) > 0)
require("compact_has_summary", isinstance(compact.get("summary"), dict))
require("compact_has_pagination", isinstance(compact.get("pagination"), dict))
require("compact_no_heavy_fields", not compact_heavy_hits, json.dumps(compact_heavy_hits[:3], ensure_ascii=False))
require("compact_bytes_under_limit", compact_bytes < max_compact_bytes, f"{compact_bytes} >= {max_compact_bytes}")
require("compact_fast", compact_ms < max_compact_ms, f"{compact_ms} >= {max_compact_ms}")

require("full_ok", full_status == 200 and full.get("ok") is True)
require("full_flag_not_compact", full.get("compact") is False)
require("summary_total_preserved", (compact.get("summary") or {}).get("total_runs") == (full.get("summary") or {}).get("total_runs"))

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

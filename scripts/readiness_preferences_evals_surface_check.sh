#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.oracle}"
PROJECT="${PROJECT:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.local.yml}"
OVERRIDE_FILE="${OVERRIDE_FILE:-docker-compose.aws.yml}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8011}"
REPORT="runtime/ai_decision_studio_functional_baseline/parity_reports/preferences_evals_surface_readiness_report.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --project)
      PROJECT="${2:?}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:?}"
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

COMPOSE_ARGS=(-p "$PROJECT" -f "$COMPOSE_FILE")
if [ -f "$OVERRIDE_FILE" ]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
fi

if docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" ps product-api >/dev/null 2>&1; then
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T product-api python - "$BASE_URL" <<'PY' | tee "$REPORT"
import json
import sys
import urllib.request
from pathlib import Path

base_url = sys.argv[1].rstrip("/")
errors = []
checks = {}
evidence = {}

def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))

def fetch_json(path):
    with urllib.request.urlopen(base_url + path, timeout=90) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))

evals = fetch_json("/api/lab/evals")

recent_totals = evals.get("recentLiveTotals")
recent_window = evals.get("recentLiveWindow")
recent_pass_rate = evals.get("recentLivePassRate")

evidence["evals_status"] = evals.get("status")
evidence["livePassRate"] = evals.get("livePassRate")
evidence["recentLivePassRate"] = recent_pass_rate
evidence["recentLiveTotals"] = recent_totals
evidence["recentLiveWindow"] = recent_window

require("evals_ok", evals.get("ok") is True)
require("recent_live_pass_rate_present", isinstance(recent_pass_rate, int), repr(recent_pass_rate))
require("recent_live_totals_present", isinstance(recent_totals, dict), repr(recent_totals))
require("recent_live_window_present", isinstance(recent_window, dict), repr(recent_window))

if isinstance(recent_totals, dict):
    for key in ["pass", "warn", "fail", "review", "total"]:
        require(f"recent_live_totals_has_{key}", key in recent_totals, repr(recent_totals))

if isinstance(recent_window, dict):
    require("recent_live_window_has_label", bool(recent_window.get("label")), repr(recent_window))
    require("recent_live_window_has_max_size", int(recent_window.get("maxSize") or 0) == 10, repr(recent_window))

payload = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}

print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)
PY
else
  python3 - "$REPORT" <<'PY'
import json
import sys
from pathlib import Path

report = Path(sys.argv[1])
payload = {
    "ok": False,
    "checks": {"product_api_container_available": False},
    "errors": ["product-api container is not available; run this check after compose up"],
    "evidence": {},
}
report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))
raise SystemExit(1)
PY
fi

echo
echo "== Source/UI string check =="
python3 - <<'PY'
from pathlib import Path
import json
import sys

paths = [
    Path("src/services/preferences.py"),
    Path("frontend/src/lib/preferences-ui.ts"),
    Path("frontend/src/pages/EvalsDiagnosisPage.tsx"),
    Path("frontend/src/lib/ai-lab-data.ts"),
    Path("src/product/lab.py"),
]

bad_patterns = [
    "macOS Keychain",
    "local macOS Keychain",
    "stored locally in the macOS Keychain",
]

required_patterns = [
    "deployment credential store",
    "Recent Live Pass",
    "All Live Checks",
    "recentLivePassRate",
    "recentLiveTotals",
    "recentLiveWindow",
]

text = "\n".join(p.read_text(encoding="utf-8") for p in paths if p.exists())

bad_hits = [pat for pat in bad_patterns if pat in text]
missing = [pat for pat in required_patterns if pat not in text]

payload = {
    "ok": not bad_hits and not missing,
    "bad_hits": bad_hits,
    "missing": missing,
}

print(json.dumps(payload, indent=2, ensure_ascii=False))

if bad_hits or missing:
    raise SystemExit(1)
PY

echo
echo "OK: Preferences/Evals surface readiness passed"

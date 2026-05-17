#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8071"
ITERATIONS=5
REPORT="runtime/ai_decision_studio_functional_baseline/parity_reports/surface_latency_report.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:?}"
      shift 2
      ;;
    --iterations)
      ITERATIONS="${2:?}"
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

python3 - "$BASE_URL" "$ITERATIONS" "$REPORT" <<'PY'
import json
import statistics
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

base_url = sys.argv[1].rstrip("/")
iterations = int(sys.argv[2])
report = Path(sys.argv[3])

paths = [
    "/health",
    "/api/product/run-history?compact=1&limit=100",
    "/api/product/artifacts?compact=1&limit=100",
    "/api/lab/overview",
    "/api/lab/runtime",
    "/api/lab/evals",
    "/api/lab/benchmarks",
    "/api/lab/evidenceops",
    "/api/product/integrations",
    "/api/preferences",
]

samples = []

for iteration in range(1, iterations + 1):
    for path in paths:
        start = time.perf_counter()
        status = None
        size = 0
        error = None

        try:
            with urllib.request.urlopen(base_url + path, timeout=180) as resp:
                raw = resp.read()
                status = resp.status
                size = len(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            status = exc.code
            size = len(raw)
            error = f"HTTPError:{exc.code}"
        except Exception as exc:
            error = repr(exc)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        samples.append({
            "iteration": iteration,
            "path": path,
            "status": status,
            "ok": bool(status and 200 <= int(status) < 400 and not error),
            "elapsed_ms": elapsed_ms,
            "size_bytes": size,
            "error": error,
        })

summary = {}

for path in paths:
    path_samples = [item for item in samples if item["path"] == path]
    values = [item["elapsed_ms"] for item in path_samples]
    ok_count = sum(1 for item in path_samples if item["ok"])
    error_count = len(path_samples) - ok_count

    if not values:
        continue

    sorted_values = sorted(values)
    p95_index = max(0, min(len(sorted_values) - 1, round((len(sorted_values) - 1) * 0.95)))

    summary[path] = {
        "count": len(values),
        "ok_count": ok_count,
        "error_count": error_count,
        "min_ms": min(values),
        "p50_ms": round(statistics.median(values), 2),
        "p95_ms": sorted_values[p95_index],
        "max_ms": max(values),
        "last_status": path_samples[-1]["status"],
        "last_size_bytes": path_samples[-1]["size_bytes"],
    }

payload = {
    "ok": all(item["ok"] for item in samples),
    "base_url": base_url,
    "iterations": iterations,
    "summary": summary,
    "samples": samples,
    "slow_threshold_ms": 2500,
    "slow_endpoints": [
        {"path": path, **stats}
        for path, stats in summary.items()
        if stats.get("p95_ms", 0) >= 2500
    ],
}

report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))

if payload["slow_endpoints"]:
    print()
    print("WARN: slow endpoints p95 >= 2500ms")
    for item in payload["slow_endpoints"]:
        print(f"- {item['path']}: p95={item['p95_ms']}ms max={item['max_ms']}ms")
PY

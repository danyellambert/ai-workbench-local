from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ENDPOINTS = {
    "health": "/health",
    "product_command_center": "/api/product/command-center",
    "product_workflows": "/api/product/workflows",
    "product_document_library": "/api/product/document-library",
    "product_run_history": "/api/product/run-history",
    "product_artifacts": "/api/product/artifacts",
    "lab_overview": "/api/lab/overview",
    "lab_runtime": "/api/lab/runtime",
    "lab_workflow_inspector": "/api/lab/workflow-inspector",
    "lab_benchmarks": "/api/lab/benchmarks",
    "lab_evals": "/api/lab/evals",
    "lab_artifacts": "/api/lab/artifacts",
    "lab_evidenceops": "/api/lab/evidenceops",
    "runtime_controls": "/api/runtime/controls",
    "preferences": "/api/preferences",
}


def fetch_json(base_url: str, path: str) -> object:
    with urlopen(f"{base_url.rstrip('/')}{path}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def summarize_payload(payload: object) -> dict[str, object]:
    text = json.dumps(payload, ensure_ascii=False)

    if not isinstance(payload, dict):
        return {
            "type": type(payload).__name__,
            "approx_json_bytes": len(text.encode("utf-8")),
        }

    summary: dict[str, object] = {
        "top_level_keys": sorted(payload.keys()),
        "approx_json_bytes": len(text.encode("utf-8")),
    }

    for key in ("documents", "runs", "artifacts", "workflows", "items", "actions"):
        value = payload.get(key)
        if isinstance(value, list):
            summary[f"{key}_count"] = len(value)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Axiovance read-only golden surface payloads.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "snapshot_kind": "golden_surface_read_only",
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": args.base_url,
        "purpose": "Parity ruler only. Not a Docker seed source.",
        "mutation_safe": True,
        "endpoints": ENDPOINTS,
        "errors": {},
    }

    summary: dict[str, object] = {}

    for name, path in ENDPOINTS.items():
        try:
            payload = fetch_json(args.base_url, path)
            (raw_dir / f"{name}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summary[name] = summarize_payload(payload)
        except HTTPError as exc:
            manifest["errors"][name] = {
                "type": "HTTPError",
                "status": exc.code,
                "reason": exc.reason,
                "path": path,
            }
        except URLError as exc:
            manifest["errors"][name] = {
                "type": "URLError",
                "reason": str(exc.reason),
                "path": path,
            }
        except Exception as exc:
            manifest["errors"][name] = {
                "type": type(exc).__name__,
                "reason": str(exc),
                "path": path,
            }

    manifest["ok"] = not bool(manifest["errors"])

    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": manifest["ok"],
        "out": str(out_dir),
        "captured": len(summary),
        "errors": manifest["errors"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

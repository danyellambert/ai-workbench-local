from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


DEFAULT_SOURCES_PATH = ROOT_DIR / "data" / "materials_demo" / "public_material_sources.json"


def _load_sources(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    materials = payload.get("materials") if isinstance(payload, dict) else []
    return [item for item in materials if isinstance(item, dict)] if isinstance(materials, list) else []


def _resolve_local_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT_DIR / path


def _download(url: str, destination: Path, *, timeout: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        destination.write_bytes(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public Phase 8 eval materials from a small curated source list.")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES_PATH), help="JSON file describing public material sources.")
    parser.add_argument("--material-id", action="append", default=[], help="Optional material_id filter. Can be repeated.")
    parser.add_argument("--force", action="store_true", help="Overwrite local files even if they already exist.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Only print the planned downloads.")
    args = parser.parse_args()

    sources_path = Path(args.sources)
    if not sources_path.is_absolute():
        sources_path = ROOT_DIR / sources_path
    materials = _load_sources(sources_path)
    selected_ids = {str(item).strip() for item in args.material_id if str(item).strip()}
    if selected_ids:
        materials = [item for item in materials if str(item.get("material_id") or "") in selected_ids]

    results: list[dict[str, object]] = []
    for item in materials:
        local_path = _resolve_local_path(str(item.get("local_path") or ""))
        exists = local_path.exists()
        action = "skip_existing" if exists and not args.force else "download"
        result = {
            "material_id": item.get("material_id"),
            "document_name": item.get("document_name"),
            "local_path": str(local_path),
            "source_url": item.get("source_url"),
            "action": action,
        }
        if args.dry_run:
            results.append(result)
            continue
        if action == "skip_existing":
            results.append(result)
            continue
        _download(str(item.get("source_url") or ""), local_path, timeout=args.timeout)
        result["downloaded_bytes"] = local_path.stat().st_size if local_path.exists() else 0
        results.append(result)

    print(json.dumps({"sources": str(sources_path), "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
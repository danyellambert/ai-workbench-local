from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.providers.registry import build_provider_registry  # noqa: E402
from src.services.phase8_5_benchmark import (  # noqa: E402
    DEFAULT_PHASE8_5_MANIFEST_PATH,
    build_preflight_payload,
    build_run_id,
    load_benchmark_manifest,
    resolve_repo_path,
    run_phase8_5_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Phase 8.5 benchmark matrix.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_PHASE8_5_MANIFEST_PATH),
        help="Path to the Phase 8.5 benchmark manifest JSON.",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Resolve the selected matrix, providers, and output paths without executing cases.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the smoke-sized subset defined in the manifest.",
    )
    parser.add_argument(
        "--group",
        action="append",
        choices=["generation", "embeddings", "rerankers", "ocr_vlm"],
        help="Benchmark group to run. Repeat the flag to run multiple groups. Defaults to all enabled groups.",
    )
    parser.add_argument("--provider", help="Optional provider filter.")
    parser.add_argument("--model", help="Optional exact model filter.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from a previous run directory and skip already successful cases.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved run plan and exit without writing outputs or executing cases.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit run directory override. Defaults to <manifest root_dir>/<stable run id>.",
    )
    return parser.parse_args()


def resolve_selected_groups(manifest: dict[str, object], requested_groups: list[str] | None) -> list[str]:
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    enabled_groups = [
        group_name
        for group_name, group_payload in groups.items()
        if isinstance(group_payload, dict) and bool(group_payload.get("enabled", True))
    ]
    if requested_groups:
        invalid = [group for group in requested_groups if group not in groups]
        if invalid:
            raise ValueError(f"Unknown benchmark groups requested: {', '.join(invalid)}")
        disabled = [group for group in requested_groups if group not in enabled_groups]
        if disabled:
            raise ValueError(f"Requested benchmark groups are disabled in the manifest: {', '.join(disabled)}")
        return list(dict.fromkeys(requested_groups))
    return enabled_groups


def resolve_run_dir(
    manifest: dict[str, object],
    *,
    run_id: str,
    output_dir_override: str | None,
) -> Path:
    if output_dir_override:
        return resolve_repo_path(output_dir_override)
    output_policy = manifest.get("output_directory_policy") if isinstance(manifest.get("output_directory_policy"), dict) else {}
    root_dir = resolve_repo_path(str(output_policy.get("root_dir") or "benchmark_runs/phase8_5_round1"))
    return root_dir / run_id


def ensure_safe_run_directory(manifest: dict[str, object], run_dir: Path, *, resume: bool) -> None:
    output_policy = manifest.get("output_directory_policy") if isinstance(manifest.get("output_directory_policy"), dict) else {}
    prevent_overwrite = bool(output_policy.get("prevent_overwrite_without_resume", True))
    raw_events_path = run_dir / "raw" / "events.jsonl"
    if prevent_overwrite and raw_events_path.exists() and not resume:
        raise RuntimeError(
            f"Run directory already contains benchmark events. Re-run with --resume or choose a different --output-dir: {run_dir}"
        )


def write_preflight_file(run_dir: Path, payload: dict[str, object]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "preflight.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    manifest = load_benchmark_manifest(args.manifest)
    registry = build_provider_registry()
    selected_groups = resolve_selected_groups(manifest, args.group)
    run_id = build_run_id(
        manifest,
        selected_groups=selected_groups,
        provider_filter=args.provider,
        model_filter=args.model,
        smoke=bool(args.smoke),
    )
    run_dir = resolve_run_dir(manifest, run_id=run_id, output_dir_override=args.output_dir)

    if not args.dry_run:
        ensure_safe_run_directory(manifest, run_dir, resume=bool(args.resume))

    preflight = build_preflight_payload(
        manifest,
        registry=registry,
        run_id=run_id,
        output_dir=run_dir,
        selected_groups=selected_groups,
        smoke=bool(args.smoke),
        provider_filter=args.provider,
        model_filter=args.model,
        resume=bool(args.resume),
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    **preflight,
                    "dry_run": True,
                    "manifest_path": manifest.get("_manifest_path"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.preflight:
        preflight_path = write_preflight_file(run_dir, preflight)
        print(json.dumps(preflight, indent=2, ensure_ascii=False))
        print(f"\nPreflight written to: {preflight_path}")
        return 0

    result = run_phase8_5_benchmark(
        manifest=manifest,
        registry=registry,
        run_id=run_id,
        run_dir=run_dir,
        selected_groups=selected_groups,
        smoke=bool(args.smoke),
        provider_filter=args.provider,
        model_filter=args.model,
        resume=bool(args.resume),
    )
    aggregated = result.get("aggregated") if isinstance(result.get("aggregated"), dict) else {}
    print(json.dumps(aggregated, indent=2, ensure_ascii=False))
    print(f"\nRun directory: {run_dir}")
    print(f"Raw events: {run_dir / 'raw' / 'events.jsonl'}")
    print(f"Markdown report: {run_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
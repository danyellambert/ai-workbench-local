from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


TEXT_SUFFIXES = {".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".env"}
ABS_PATH_RE = re.compile(r"""(?:/Users/[^"'\n\r,}\]]*|/private/[^"'\n\r,}\]]*|/var/folders/[^"'\n\r,}\]]*)""")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|passwd|authorization|bearer)\s*[:=]")
FORBIDDEN_EXTERNAL_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
}


def sha_short(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def collect_absolute_paths(root: Path) -> set[str]:
    found: set[str] = set()
    for path in iter_text_files(root):
        text = read_text(path)
        for match in ABS_PATH_RE.findall(text):
            cleaned = match.strip()
            if cleaned:
                found.add(cleaned)
    return found


def should_copy_external_file(src: Path) -> bool:
    """Return False for local secret/config files that must never enter the baseline."""
    name = src.name.lower()

    if name in FORBIDDEN_EXTERNAL_FILE_NAMES or name.startswith(".env."):
        return False

    if src.suffix.lower() == ".env":
        return False

    if src.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = src.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False

        if SECRET_RE.search(text):
            return False

    return True



def looks_like_safe_external_path(raw_path: str) -> bool:
    """Filter false-positive absolute paths captured from markdown tables/log blobs."""
    if len(raw_path) > 1024:
        return False

    if "\\n" in raw_path or "\\r" in raw_path:
        return False

    if "|" in raw_path:
        return False

    if raw_path.count("/Users/") + raw_path.count("/private/") + raw_path.count("/var/folders/") > 1:
        return False

    return True

def copy_external_files(paths: set[str], external_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    external_dir.mkdir(parents=True, exist_ok=True)

    for raw_path in sorted(paths):
        if not looks_like_safe_external_path(raw_path):
            continue

        try:
            src = Path(raw_path)
            if not src.exists() or not src.is_file():
                continue
        except OSError:
            continue

        if not should_copy_external_file(src):
            continue

        name = src.name
        dst_name = f"{sha_short(raw_path)}_{name}"
        dst = external_dir / dst_name
        shutil.copy2(src, dst)
        mapping[raw_path] = f"baseline://external_files/{dst_name}"

    return mapping


def build_rewrite_map(workspace_root: str, absolute_paths: set[str], external_file_map: dict[str, str]) -> dict[str, str]:
    mapping: dict[str, str] = {}

    workspace = workspace_root.rstrip("/")
    mapping[f"{workspace}/.runtime"] = "baseline://runtime"
    mapping[f"{workspace}/artifacts"] = "baseline://artifacts"
    mapping[f"{workspace}/outputs"] = "baseline://outputs"
    mapping[f"{workspace}/data"] = "baseline://data"
    mapping[workspace] = "baseline://workspace"

    for source, target in external_file_map.items():
        mapping[source] = target

    known_roots = [
        "/Users/danyellambert/Downloads/Corpus_revisado/option_a_public_corpus_v2",
        "/Users/danyellambert/ppt_creator_app/outputs/ai_workbench_export_previews",
        "/Users/danyellambert/ppt_creator_app/outputs/ai_workbench_export_smoke_suite_previews",
        "/Users/danyellambert/ppt_creator_app/outputs/beautification_targeted_previews",
        "/private/hybrid cloud",
    ]

    for root in known_roots:
        if any(path.startswith(root) for path in absolute_paths):
            logical = "baseline://external/" + root.strip("/").replace("/", "_").replace(" ", "_")
            mapping[root] = logical

    # Final sanitization fallback: every remaining absolute path must be rewritten,
    # even when the source file/dir does not exist locally or is only a legacy label.
    for path in absolute_paths:
        if path not in mapping and not any(path.startswith(source) for source in mapping):
            mapping[path] = f"baseline://unresolved_external/{sha_short(path)}"

    return dict(sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True))


def rewrite_text_files(root: Path, rewrite_map: dict[str, str]) -> list[dict[str, object]]:
    report: list[dict[str, object]] = []

    for path in iter_text_files(root):
        original = read_text(path)
        updated = original
        replacements = []

        for source, target in rewrite_map.items():
            count = updated.count(source)
            if count:
                updated = updated.replace(source, target)
                replacements.append({"source": source, "target": target, "count": count})

        if updated != original:
            write_text(path, updated)
            report.append({
                "path": str(path.relative_to(root)),
                "replacement_count": sum(item["count"] for item in replacements),
                "replacements": replacements[:20],
            })

    return report


def scan_after(root: Path) -> dict[str, object]:
    absolute_findings = []
    secret_findings = []

    for path in iter_text_files(root):
        text = read_text(path)
        abs_hits = sorted(set(ABS_PATH_RE.findall(text)))
        secret_hit = bool(SECRET_RE.search(text))

        if abs_hits:
            absolute_findings.append({
                "path": str(path.relative_to(root)),
                "hits": abs_hits[:20],
            })

        if secret_hit:
            secret_findings.append({
                "path": str(path.relative_to(root)),
            })

    return {
        "absolute_path_findings": absolute_findings,
        "secret_pattern_findings": secret_findings,
        "remaining_absolute_path_file_count": len(absolute_findings),
        "secret_pattern_file_count": len(secret_findings),
    }


def count_files(root: Path) -> dict[str, int]:
    total = 0
    by_suffix: dict[str, int] = {}

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        total += 1
        suffix = path.suffix.lower() or "<no_suffix>"
        by_suffix[suffix] = by_suffix.get(suffix, 0) + 1

    return {"total_files": total, "suffix_kinds": len(by_suffix), "by_suffix": dict(sorted(by_suffix.items()))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-stage", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    raw_stage = Path(args.raw_stage).resolve()
    out = Path(args.out).resolve()
    raw_sources = raw_stage / "raw_sources"
    raw_manifest = raw_stage / "manifest.json"

    if not raw_sources.exists():
        raise SystemExit(f"Missing raw_sources: {raw_sources}")
    if not raw_manifest.exists():
        raise SystemExit(f"Missing raw manifest: {raw_manifest}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    baseline_root = out / "baseline"
    shutil.copytree(raw_sources, baseline_root)

    manifest = json.loads(raw_manifest.read_text(encoding="utf-8"))
    workspace_root = str(manifest.get("workspace_root") or "")

    before_paths = collect_absolute_paths(baseline_root)
    external_file_map = copy_external_files(before_paths, baseline_root / "external_files")
    rewrite_map = build_rewrite_map(workspace_root, before_paths, external_file_map)
    rewrite_report = rewrite_text_files(baseline_root, rewrite_map)

    # Second pass: catch any absolute paths that remain after broad/root rewrites.
    post_initial_audit = scan_after(baseline_root)
    fallback_map: dict[str, str] = {}
    for finding in post_initial_audit.get("absolute_path_findings", []):
        for hit in finding.get("hits", []):
            fallback_map[hit] = f"baseline://unresolved_external/{sha_short(hit)}"

    if fallback_map:
        fallback_report = rewrite_text_files(baseline_root, fallback_map)
        rewrite_map.update(fallback_map)
        rewrite_report.extend(fallback_report)

    audit_after = scan_after(baseline_root)

    result_manifest = {
        "baseline_kind": "sanitized_functional_baseline_candidate",
        "source_raw_stage": str(raw_stage),
        "workspace_root_was": workspace_root,
        "baseline_root": "baseline",
        "counts_from_raw_stage": manifest.get("counts", {}),
        "file_inventory": count_files(baseline_root),
        "path_rewrite": {
            "absolute_paths_seen_before": len(before_paths),
            "rewrite_rules": len(rewrite_map),
            "files_rewritten": len(rewrite_report),
            "external_files_copied": len(external_file_map),
        },
        "audit_after": {
            "remaining_absolute_path_file_count": audit_after["remaining_absolute_path_file_count"],
            "secret_pattern_file_count": audit_after["secret_pattern_file_count"],
        },
        "docker_ready": audit_after["remaining_absolute_path_file_count"] == 0 and audit_after["secret_pattern_file_count"] == 0,
    }

    (out / "manifest.json").write_text(json.dumps(result_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "uri_rewrite_map.json").write_text(json.dumps(rewrite_map, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "path_rewrite_report.json").write_text(json.dumps(rewrite_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "audit_after.json").write_text(json.dumps(audit_after, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(result_manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

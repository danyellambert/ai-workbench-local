#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_DIR:-${AI_DECISION_STUDIO_ORACLE_BUNDLE_DIR:-runtime/ai_decision_studio_functional_baseline/deployment_bundle}}"
BUNDLE_NAME="${AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_NAME:-${AI_DECISION_STUDIO_ORACLE_BUNDLE_NAME:-ai-decision-studio-app-bundle}}"
BUNDLE_ROOT="$OUT_DIR/$BUNDLE_NAME"
ARCHIVE_PATH="$OUT_DIR/${BUNDLE_NAME}.tar.gz"
REPORT="${AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_REPORT:-${AI_DECISION_STUDIO_ORACLE_BUNDLE_REPORT:-runtime/ai_decision_studio_functional_baseline/parity_reports/deployment_bundle_report.json}}"

export OUT_DIR
export BUNDLE_NAME
export BUNDLE_ROOT
export ARCHIVE_PATH
export REPORT

echo "== Build deployment bundle =="
echo "out_dir=$OUT_DIR"
echo "bundle_root=$BUNDLE_ROOT"
echo "archive=$ARCHIVE_PATH"
echo "report=$REPORT"

rm -rf "$BUNDLE_ROOT" "$ARCHIVE_PATH"
mkdir -p "$BUNDLE_ROOT" "$(dirname "$REPORT")"

copy_path() {
  SRC="$1"
  DST="$BUNDLE_ROOT/$SRC"

  if [ ! -e "$SRC" ]; then
    echo "ERROR: missing required path: $SRC" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$DST")"

  if [ -d "$SRC" ]; then
    if command -v rsync >/dev/null 2>&1; then
      rsync -a \
        --exclude node_modules \
        --exclude dist \
        --exclude .vite \
        --exclude .pytest_cache \
        --exclude __pycache__ \
        --exclude '*.pyc' \
        --exclude .DS_Store \
        --exclude '._*' \
        "$SRC"/ "$DST"/
    else
      cp -R "$SRC" "$DST"
    fi
  else
    cp "$SRC" "$DST"
  fi
}

copy_path "docker-compose.oracle-like.yml"
copy_path ".env.aws.example"
copy_path ".env.docker.example"
copy_path ".env.local.example"
copy_path ".dockerignore"
copy_path "Dockerfile.public-demo"
copy_path "Dockerfile.aws-slim-product-api"
copy_path "requirements-aws-slim.txt"
copy_path "docker-compose.aws-slim.override.yml"
copy_path "Dockerfile.frontend-public-demo"
copy_path "requirements-public-demo.txt"
copy_path "main_product_api.py"

copy_path "src"
copy_path "frontend"

copy_path "docs/deployment"
copy_path "services/ppt_creator_app"


copy_path "scripts/cleanup_public_session_overlays.py"
copy_path "docs/deployment/NEXTCLOUD_GOLDEN_BASELINE_RESTORE.md"
copy_path "scripts/readiness_nextcloud_golden_baseline_check.sh"
copy_path "scripts/restore_nextcloud_golden_baseline.sh"
copy_path "docs/deployment/AI_LAB_GOLDEN_STATE_RESTORE.md"
copy_path "scripts/readiness_ai_lab_golden_state_check.sh"
copy_path "scripts/readiness_public_ai_lab_overlay_check.sh"
copy_path "scripts/readiness_preferences_evals_surface_check.sh"
copy_path "scripts/readiness_required_integrations_check.sh"
copy_path "scripts/readiness_trello_public_visibility_check.sh"
copy_path "scripts/readiness_final_deploy_check.sh"
copy_path "scripts/readiness_evidenceops_ui_cache_check.sh"
copy_path "scripts/readiness_run_history_compact_check.sh"
copy_path "scripts/readiness_artifacts_compact_check.sh"
copy_path "scripts/readiness_candidate_review_contract_check.sh"
copy_path "docs/deployment/REDEPLOY_FAST_PATH.md"
copy_path "scripts/measure_surface_latency.sh"
copy_path "scripts/readiness_required_providers_check.sh"
copy_path "scripts/readiness_admin_session_isolation_check.sh"
copy_path "scripts/build_deployment_bundle.sh"
copy_path "scripts/build_oracle_deployment_bundle.sh"
copy_path "scripts/deploy_aws_slim.sh"
copy_path "scripts/smoke_aws_slim.sh"
copy_path "scripts/validate_aws_env_contract.py"
copy_path "scripts/readiness_multi_environment_contract_check.sh"
copy_path "scripts/run_local_docker.sh"
copy_path "scripts/run_local_dev.sh"
copy_path "scripts/restore_ai_lab_golden_state.sh"

copy_path "scripts/readiness_phase_13_2_public_session_retention_check.sh"

find "$BUNDLE_ROOT" \( -name ".DS_Store" -o -name "._*" \) -type f -delete

python3 - <<'PY'
import json
import os
import re
from pathlib import Path

bundle_root = Path(os.environ["BUNDLE_ROOT"]).resolve()
report_path = Path(os.environ["REPORT"]).resolve()

forbidden_names = {".env", ".env.local", ".env.docker", ".env.docker.local", ".env.aws", ".env.aws.local", ".env.oracle", ".env.oracle.local", ".env.production", ".env.production.local"}

def count_files(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file())

def forbidden_files(path: Path) -> list[str]:
    found = []
    for item in path.rglob("*"):
        if item.is_file() and item.name in forbidden_names:
            found.append(str(item.relative_to(path)))
    return found

def heavy_or_runtime_paths(path: Path) -> list[str]:
    hits = []
    blocked_parts = {
        "oracle_like_data",
        "current_sanitized_baseline",
        "current_frontend_parity_overlay",
        "parity_reports",
        ".runtime",
        "node_modules",
    }

    for item in path.rglob("*"):
        rel_parts = set(item.relative_to(path).parts)
        if rel_parts & blocked_parts:
            hits.append(str(item.relative_to(path)))
            if len(hits) >= 50:
                break

    return hits

def looks_real_secret_value(value: str) -> bool:
    value = value.strip().strip(",").strip().strip("\"'")
    lowered = value.lower()

    if not value:
        return False

    if lowered in {
        "none",
        "null",
        "undefined",
        "false",
        "true",
        "redacted",
        "***redacted***",
        "set",
        "changeme",
        "change_me",
        "your_value_here",
    }:
        return False

    if value.startswith("${") or value.startswith("$") or value.startswith("<"):
        return False

    if lowered.startswith("os.environ") or lowered.startswith("process.env"):
        return False

    if "getenv(" in lowered or ".get(" in lowered:
        return False

    return len(value) >= 12

def secret_findings(path: Path, limit: int = 50) -> list[dict]:
    findings = []

    # The bundle intentionally contains source code. Source code naturally has names
    # like api_key, max_tokens, TOKEN_PATTERN and password fields. Those are not
    # leaked secrets. Only inspect deploy/config files where literal secret values
    # are likely to be accidentally committed.
    inspect_names = {
    ".env.aws.example",
    ".env.docker.example",
    ".env.local.example",
        "docker-compose.oracle-like.yml",
        "docker-compose.yml",
        "docker-compose.yaml",
    }
    inspect_suffixes = {".env", ".example", ".yml", ".yaml", ".json", ".toml", ".ini"}

    env_secret_re = re.compile(
        r"(?i)^\s*([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|PASSWORD|PASSWD|AUTHORIZATION|BEARER|SECRET)[A-Z0-9_]*)\s*=\s*(.+?)\s*$"
    )
    yaml_json_secret_re = re.compile(
        r"(?i)[\"']?(api[_-]?key|apikey|token|password|passwd|authorization|bearer|secret)[\"']?\s*:\s*[\"']([^\"']+)[\"']"
    )

    for item in path.rglob("*"):
        if len(findings) >= limit:
            break

        if not item.is_file():
            continue

        if item.name not in inspect_names and item.suffix.lower() not in inspect_suffixes:
            continue

        if item.stat().st_size > 1_000_000:
            continue

        try:
            text = item.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()

            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue

            matches = []

            env_match = env_secret_re.search(stripped)
            if env_match:
                matches.append((env_match.group(1), env_match.group(2)))

            yaml_match = yaml_json_secret_re.search(stripped)
            if yaml_match:
                matches.append((yaml_match.group(1), yaml_match.group(2)))

            for key, value in matches:
                if looks_real_secret_value(value):
                    findings.append({
                        "path": str(item.relative_to(path)),
                        "line": lineno,
                        "key": key,
                    })
                    break

            if len(findings) >= limit:
                break

    return findings

required_paths = [
    "docker-compose.oracle-like.yml",
    ".env.aws.example",
    ".env.docker.example",
    ".env.local.example",
    "Dockerfile.public-demo",
    "Dockerfile.frontend-public-demo",
    "requirements-public-demo.txt",
    "main_product_api.py",
    "src",
    "frontend",
    "services/ppt_creator_app/Dockerfile",
    "services/ppt_creator_app/pyproject.toml",
    "services/ppt_creator_app/bin/run_ppt_creator_api_container.sh",
    "scripts/cleanup_public_session_overlays.py",
    "docs/deployment/NEXTCLOUD_GOLDEN_BASELINE_RESTORE.md",
    "scripts/readiness_nextcloud_golden_baseline_check.sh",
    "scripts/restore_nextcloud_golden_baseline.sh",
    "docs/deployment/AI_LAB_GOLDEN_STATE_RESTORE.md",
    "scripts/readiness_ai_lab_golden_state_check.sh",
    "scripts/readiness_public_ai_lab_overlay_check.sh",
    "scripts/readiness_preferences_evals_surface_check.sh",
    "scripts/readiness_required_integrations_check.sh",
    "scripts/readiness_trello_public_visibility_check.sh",
    "scripts/readiness_final_deploy_check.sh",
    "scripts/readiness_evidenceops_ui_cache_check.sh",
    "scripts/readiness_run_history_compact_check.sh",
    "scripts/readiness_artifacts_compact_check.sh",
    "scripts/readiness_candidate_review_contract_check.sh",
    "docs/deployment/REDEPLOY_FAST_PATH.md",
    "docs/deployment/MULTI_ENVIRONMENT_CONTRACT.md",
    "docs/deployment/AWS_FRESH_EC2_BOOTSTRAP.md",
    "scripts/measure_surface_latency.sh",
    "scripts/readiness_required_providers_check.sh",
    "scripts/readiness_admin_session_isolation_check.sh",
    "scripts/deploy_aws_slim.sh",
    "scripts/smoke_aws_slim.sh",
    "scripts/validate_aws_env_contract.py",
    "scripts/readiness_multi_environment_contract_check.sh",
    "scripts/run_local_docker.sh",
    "scripts/run_local_dev.sh",
    "scripts/restore_ai_lab_golden_state.sh",
]

checks = {
    "bundle_root_exists": bundle_root.exists(),
    "required_paths_present": all((bundle_root / item).exists() for item in required_paths),
    "no_real_env_files": not forbidden_files(bundle_root),
    "no_secret_findings": not secret_findings(bundle_root),
    "no_runtime_or_baseline_data": not heavy_or_runtime_paths(bundle_root),
    "no_macos_metadata": not list(bundle_root.rglob(".DS_Store")) and not list(bundle_root.rglob("._*")),
    "file_count_gt_20": count_files(bundle_root) > 20,
}

report = {
    "ok": all(checks.values()),
    "checks": checks,
    "bundle_root": str(bundle_root),
    "file_count": count_files(bundle_root),
    "forbidden_files": forbidden_files(bundle_root),
    "secret_findings": secret_findings(bundle_root),
    "runtime_or_heavy_path_findings": heavy_or_runtime_paths(bundle_root),
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY

tar -czf "$ARCHIVE_PATH" -C "$OUT_DIR" "$BUNDLE_NAME"

echo
echo "== Bundle created =="
ls -lh "$ARCHIVE_PATH"

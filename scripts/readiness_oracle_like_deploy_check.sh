#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE:-docker-compose.oracle-like.yml}"
ENV_EXAMPLE="${AI_DECISION_STUDIO_ORACLE_ENV_EXAMPLE:-.env.oracle.example}"
REPORT="${AI_DECISION_STUDIO_ORACLE_READINESS_REPORT:-../ai_decision_studio_functional_baseline/parity_reports/oracle_like_deploy_readiness_report.json}"

mkdir -p "$(dirname "$REPORT")"

echo "== Oracle-like deployment readiness check =="
echo "compose=$COMPOSE_FILE"
echo "env_example=$ENV_EXAMPLE"
echo "report=$REPORT"

python3 - <<'PY'
import json
import os
import re
import subprocess
from pathlib import Path

compose_file = Path(os.environ.get("AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE", "docker-compose.oracle-like.yml"))
env_example = Path(os.environ.get("AI_DECISION_STUDIO_ORACLE_ENV_EXAMPLE", ".env.oracle.example"))
report_path = Path(os.environ.get("AI_DECISION_STUDIO_ORACLE_READINESS_REPORT", "../ai_decision_studio_functional_baseline/parity_reports/oracle_like_deploy_readiness_report.json"))

secret_patterns = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\\s'\"]+")

def run(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return {"ok": True, "output": out}
    except subprocess.CalledProcessError as exc:
        return {"ok": False, "output": exc.output}

compose_text = compose_file.read_text(encoding="utf-8") if compose_file.exists() else ""
env_text = env_example.read_text(encoding="utf-8") if env_example.exists() else ""

compose_config = run(["docker", "compose", "-f", str(compose_file), "config", "-q"]) if compose_file.exists() else {"ok": False, "output": "compose file missing"}

required_env_names = [
    "AI_DECISION_STUDIO_BASELINE_ROOT",
    "AI_DECISION_STUDIO_RUNTIME_ROOT",
    "AI_DECISION_STUDIO_ARTIFACT_ROOT",
    "AI_DECISION_STUDIO_USERS_ROOT",
    "OLLAMA_BASE_URL",
    "OLLAMA_HOSTED_API_KEY",
    "HUGGINGFACE_INFERENCE_API_KEY",
    "EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD",
    "EVIDENCEOPS_TRELLO_API_KEY",
    "EVIDENCEOPS_NOTION_API_KEY",
]

env_declared = {
    line.split("=", 1)[0].strip()
    for line in env_text.splitlines()
    if line and not line.strip().startswith("#") and "=" in line
}

raw_secret_hits = []
for path in [compose_file, env_example]:
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if secret_patterns.search(stripped):
            key, _, value = stripped.partition("=")
            if value.strip():
                raw_secret_hits.append({"path": str(path), "line": lineno, "key": key.strip()})

host_docker_internal_mentions = [
    {"path": str(compose_file), "line": lineno, "text": line.strip()}
    for lineno, line in enumerate(compose_text.splitlines(), start=1)
    if "host.docker.internal" in line
]

checks = {
    "compose_exists": compose_file.exists(),
    "compose_config_valid": compose_config["ok"],
    "env_example_exists": env_example.exists(),
    "env_example_declares_required_names": all(name in env_declared for name in required_env_names),
    "env_example_has_no_real_secret_values": not raw_secret_hits,
    "deployment_plan_exists": Path("docs/deployment/ORACLE_ALWAYS_FREE_DEPLOYMENT_PLAN.md").exists(),
    "operations_runbook_exists": Path("docs/deployment/ORACLE_OPERATIONS_RUNBOOK.md").exists(),
    "oracle_compose_smoke_exists": Path("scripts/smoke_oracle_like_compose.sh").exists(),
    "frontend_dockerfile_exists": Path("Dockerfile.frontend-public-demo").exists(),
    "product_api_dockerfile_exists": Path("Dockerfile.public-demo").exists(),
}

warnings = []
if host_docker_internal_mentions:
    warnings.append({
        "code": "host_docker_internal_local_only",
        "message": "Compose/runtime still mentions host.docker.internal. This is acceptable for local validation but must be replaced or explicitly supported on Oracle.",
        "mentions": host_docker_internal_mentions,
    })

report = {
    "ok": all(checks.values()),
    "checks": checks,
    "warnings": warnings,
    "evidence": {
        "compose_file": str(compose_file),
        "env_example": str(env_example),
        "declared_env_count": len(env_declared),
        "raw_secret_hits": raw_secret_hits,
        "compose_config_output": compose_config["output"][:2000],
    },
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Oracle-like deployment readiness check completed =="

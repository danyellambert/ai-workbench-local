#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 13.2 Oracle exposure readiness =="

python3 - <<'PY'
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

compose_path = Path("docker-compose.oracle-like.yml")
env_example_path = Path(".env.oracle.example")
caddy_path = Path("legacy/deploy/oracle/Caddyfile.example")
checklist_path = Path("legacy/docs/deployment/oracle/ORACLE_ALWAYS_FREE_SECURITY_EXPOSURE_CHECKLIST.md")

checks: dict[str, bool] = {}
evidence: dict[str, object] = {}
errors: list[str] = []

def require(name: str, condition: bool, detail: object | None = None) -> None:
    checks[name] = bool(condition)
    if detail is not None:
        evidence[name] = detail
    if not condition:
        errors.append(name)

compose = compose_path.read_text(encoding="utf-8") if compose_path.exists() else ""
env_example = env_example_path.read_text(encoding="utf-8") if env_example_path.exists() else ""
caddy = caddy_path.read_text(encoding="utf-8") if caddy_path.exists() else ""
checklist = checklist_path.read_text(encoding="utf-8") if checklist_path.exists() else ""

require("compose_exists", compose_path.exists())
require("env_example_exists", env_example_path.exists())
require("caddyfile_example_exists", caddy_path.exists())
require("security_checklist_exists", checklist_path.exists())

try:
    subprocess.run(
        ["docker", "compose", "-f", str(compose_path), "config"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    compose_config_valid = True
except Exception as exc:
    compose_config_valid = False
    evidence["compose_config_error"] = str(exc)

require("compose_config_valid", compose_config_valid)

product_match = re.search(r"(?ms)^  product-api:\n(.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)", compose)
product_block = product_match.group(1) if product_match else ""

require("product_api_service_found", bool(product_match))
require("product_api_has_no_ports_block", "ports:" not in product_block, product_block[:800])
require("product_api_expose_only", "expose:" in product_block and "8011" in product_block)

frontend_match = re.search(r"(?ms)^  frontend:\n(.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)", compose)
frontend_block = frontend_match.group(1) if frontend_match else ""

require("frontend_service_found", bool(frontend_match))
require(
    "frontend_binds_localhost_by_default",
    "${AI_DECISION_STUDIO_FRONTEND_BIND_HOST:-127.0.0.1}:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8080}:8080" in frontend_block,
    frontend_block[:800],
)

for key in [
    "AI_DECISION_STUDIO_FRONTEND_BIND_HOST",
    "AI_DECISION_STUDIO_PUBLIC_DOMAIN",
    "AI_DECISION_STUDIO_ACME_EMAIL",
    "AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB",
]:
    require(f"env_declares_{key}", key in env_example)

require("caddy_uses_public_domain_env", "{$AI_DECISION_STUDIO_PUBLIC_DOMAIN}" in caddy)
require("caddy_reverse_proxies_to_local_frontend", "reverse_proxy 127.0.0.1:{$AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT}" in caddy)
require("caddy_has_security_headers", "X-Content-Type-Options" in caddy and "Referrer-Policy" in caddy)

for token in [
    "80/tcp",
    "443/tcp",
    "22/tcp",
    "8011/tcp",
    "8787/tcp",
    "11434/tcp",
    "8085/tcp",
    "8080/tcp",
]:
    require(f"checklist_mentions_{token.replace('/', '_')}", token in checklist)

payload = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}
print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)

print("OK: Phase 13.2 Oracle exposure readiness passed")
PY

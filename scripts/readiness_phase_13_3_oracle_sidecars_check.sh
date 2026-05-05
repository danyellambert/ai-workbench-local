#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 13.3 Oracle sidecar readiness =="

python3 - <<'PY'
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

compose_path = Path("docker-compose.oracle-like.yml")
env_path = Path(".env.oracle.example")
bundle_script_path = Path("scripts/build_oracle_deployment_bundle.sh")
ppt_root = Path("services/ppt_creator_app")

checks = {}
errors = {}
evidence = {}

def require(name: str, condition: bool, detail=None) -> None:
    checks[name] = bool(condition)
    if detail is not None:
        evidence[name] = detail
    if not condition:
        errors[name] = detail if detail is not None else False

compose = compose_path.read_text(encoding="utf-8") if compose_path.exists() else ""
env_text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
bundle_script = bundle_script_path.read_text(encoding="utf-8") if bundle_script_path.exists() else ""

require("ppt_creator_service_source_exists", ppt_root.exists())
for rel in [
    "legacy/docker/Dockerfile.legacy-streamlit",
    "pyproject.toml",
    "bin/run_ppt_creator_api_container.sh",
    "ppt_creator",
    "ppt_creator_ai",
]:
    require(f"ppt_creator_has_{rel.replace('/', '_')}", (ppt_root / rel).exists())

bad_metadata = []
if ppt_root.exists():
    for item in ppt_root.rglob("*"):
        if item.name in {".git", "__MACOSX", ".DS_Store", ".pytest_cache", ".ruff_cache", ".vscode", "outputs"} or item.name.startswith("._") or item.suffix == ".pyc":
            bad_metadata.append(str(item.relative_to(ppt_root)))
            if len(bad_metadata) >= 20:
                break
require("ppt_creator_source_clean", not bad_metadata, bad_metadata)

try:
    proc = subprocess.run(
        ["docker", "compose", "-f", str(compose_path), "config"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require("compose_config_valid", proc.returncode == 0, proc.stderr[-1000:])
except Exception as exc:
    require("compose_config_valid", False, str(exc))

def service_block(name: str) -> str:
    match = re.search(rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-zA-Z0-9_-]+:|\nvolumes:|\nnetworks:|\Z)", compose)
    return match.group(1) if match else ""

for service in ["product-api", "frontend", "ppt-creator", "ollama", "nextcloud"]:
    block = service_block(service)
    require(f"{service}_service_exists", bool(block), block[:1000])

for service, port in [
    ("product-api", "8011"),
    ("ppt-creator", "8787"),
    ("ollama", "11434"),
    ("nextcloud", "80"),
]:
    block = service_block(service)
    require(f"{service}_has_no_public_ports_block", "ports:" not in block, block[:1000])
    require(f"{service}_exposes_{port}", "expose:" in block and port in block, block[:1000])

frontend_block = service_block("frontend")
require("frontend_still_binds_localhost", "127.0.0.1" in frontend_block and "ports:" in frontend_block, frontend_block[:1000])

product_block = service_block("product-api")
for service in ["ppt-creator", "ollama", "nextcloud"]:
    require(f"product_api_depends_on_{service}", service in product_block, product_block[:1200])

require("product_api_uses_internal_ppt_creator", "http://ppt-creator:8787" in product_block)
require("product_api_uses_internal_ollama", "http://ollama:11434/v1" in product_block)
require("product_api_uses_internal_nextcloud", "http://nextcloud/remote.php/dav/files/ads_admin" in product_block)

for key in [
    "NEXTCLOUD_ADMIN_USER",
    "NEXTCLOUD_ADMIN_PASSWORD",
    "NEXTCLOUD_TRUSTED_DOMAINS",
    "OLLAMA_CPUS",
    "OLLAMA_MEM_LIMIT",
    "OLLAMA_MEMSWAP_LIMIT",
    "OLLAMA_MAX_LOADED_MODELS",
    "OLLAMA_NUM_PARALLEL",
    "PPT_CREATOR_AI_SERVICE_URL",
]:
    require(f"env_declares_{key}", key in env_text)

require("bundle_includes_ppt_creator_service", 'copy_path "services/ppt_creator_app"' in bundle_script)
require("bundle_requires_ppt_creator_dockerfile", '"services/ppt_creator_app/Dockerfile"' in bundle_script)

payload = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}
print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)

print("OK: Phase 13.3 Oracle sidecar readiness passed")
PY

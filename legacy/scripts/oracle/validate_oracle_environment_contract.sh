#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.oracle}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  echo "Create .env.oracle from .env.oracle.example and fill deployment secrets outside Git." >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

missing=()

require_nonempty() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" ]]; then
    missing+=("$name")
  fi
}

require_nonempty AI_DECISION_STUDIO_BASELINE_ROOT
require_nonempty AI_DECISION_STUDIO_RUNTIME_ROOT
require_nonempty AI_DECISION_STUDIO_ARTIFACT_ROOT
require_nonempty AI_DECISION_STUDIO_USERS_ROOT
require_nonempty AI_DECISION_STUDIO_ADMIN_USERNAME
require_nonempty AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH
require_nonempty AI_DECISION_STUDIO_SESSION_SECRET

if [[ "${PRESENTATION_EXPORT_ENABLED:-}" =~ ^(true|1|yes)$ ]]; then
  require_nonempty PRESENTATION_EXPORT_BASE_URL
fi

if [[ "${EVIDENCEOPS_REPOSITORY_BACKEND:-}" == "nextcloud_webdav" ]]; then
  require_nonempty EVIDENCEOPS_NEXTCLOUD_BASE_URL
  require_nonempty EVIDENCEOPS_NEXTCLOUD_USERNAME
  require_nonempty EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD
  require_nonempty EVIDENCEOPS_NEXTCLOUD_ROOT_PATH
fi

if (( ${#missing[@]} > 0 )); then
  echo "ERROR: missing required env values:" >&2
  printf ' - %s\n' "${missing[@]}" >&2
  exit 1
fi

bad_loopback=()

check_container_loopback() {
  local name="$1"
  local value="${!name:-}"
  if [[ "$value" == http://127.0.0.1:* || "$value" == http://localhost:* ]]; then
    bad_loopback+=("$name=$value")
  fi
}

check_container_loopback OLLAMA_BASE_URL
check_container_loopback OLLAMA_HOST
check_container_loopback EVIDENCEOPS_NEXTCLOUD_BASE_URL
check_container_loopback PRESENTATION_EXPORT_BASE_URL

if (( ${#bad_loopback[@]} > 0 )); then
  echo "ERROR: container-facing env points to localhost/127.0.0.1." >&2
  echo "Inside product-api, localhost means the product-api container, not the Oracle host." >&2
  printf ' - %s\n' "${bad_loopback[@]}" >&2
  echo "Use service DNS or host.docker.internal with extra_hosts." >&2
  exit 1
fi

for dir_name in AI_DECISION_STUDIO_RUNTIME_ROOT AI_DECISION_STUDIO_ARTIFACT_ROOT AI_DECISION_STUDIO_USERS_ROOT; do
  dir="${!dir_name:-}"
  if [[ -d "$dir" && ! -w "$dir" ]]; then
    echo "ERROR: $dir_name exists but is not writable: $dir" >&2
    exit 1
  fi
done

if [[ -d "${AI_DECISION_STUDIO_BASELINE_ROOT:-}" && ! -r "${AI_DECISION_STUDIO_BASELINE_ROOT:-}" ]]; then
  echo "ERROR: baseline root exists but is not readable: $AI_DECISION_STUDIO_BASELINE_ROOT" >&2
  exit 1
fi

echo "OK: Oracle environment contract looks configured."
echo "Checked env file: $ENV_FILE"
echo "Presentation export base URL: ${PRESENTATION_EXPORT_BASE_URL:-<disabled/missing>}"
echo "EvidenceOps backend: ${EVIDENCEOPS_REPOSITORY_BACKEND:-<unset>}"

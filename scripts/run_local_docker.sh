#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.docker}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
CONFIG_ONLY="false"
DOWN_ONLY="false"
NO_BUILD="false"
SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE="${SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE:-0}"
SKIP_AI_LAB_GOLDEN_STATE_RESTORE="${SKIP_AI_LAB_GOLDEN_STATE_RESTORE:-0}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_local_docker.sh
  scripts/run_local_docker.sh --config-only
  scripts/run_local_docker.sh --down
  scripts/run_local_docker.sh --no-build

Optional env:
  ENV_FILE=.env.docker
  COMPOSE_PROJECT_NAME=ai-decision-studio
  SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE=1
  SKIP_AI_LAB_GOLDEN_STATE_RESTORE=1

Behavior:
  - Uses docker-compose.local.yml as the local Docker topology.
  - Does not use AWS slim override.
  - Frontend container serves the app through Nginx.
  - Nginx proxies /api and /health to product-api:8011 inside Docker.
  - Vite local-dev proxy is not used for Docker.
  - Ensures the local Docker Nextcloud volume has the golden baseline:
      data/danyel/files/EvidenceOpsDemo
  - Restores the baseline from an external tarball when the volume is empty/missing it.
  - --config-only renders compose config without building or starting containers.
  - --down stops/removes compose containers without removing volumes.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --config-only)
      CONFIG_ONLY="true"
      shift
      ;;
    --down)
      DOWN_ONLY="true"
      shift
      ;;
    --no-build)
      NO_BUILD="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  echo "Create it from .env.docker.example and adjust local data-root paths/secrets." >&2
  exit 1
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1" >&2
    exit 1
  fi
}

require_command docker
require_command grep

compose() {
  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT_NAME" \
    -f docker-compose.local.yml \
    "$@"
}

get_env_value() {
  key="$1"
  default="$2"
  awk -F= -v k="$key" -v d="$default" '
    $1 == k {
      v = substr($0, index($0, "=") + 1)
    }
    END {
      if (v == "") print d
      else {
        gsub(/^"|"$/, "", v)
        gsub(/^'\''|'\''$/, "", v)
        print v
      }
    }
  ' "$ENV_FILE"
}

compose_project_has_running_containers() {
  docker ps \
    --filter "label=com.docker.compose.project=$PROJECT_NAME" \
    --format '{{.Names}}' \
    | grep -q .
}

volume_has_nextcloud_golden_baseline() {
  local volume="$1"
  local user="$2"
  local root_path="$3"

  docker run --rm \
    -e NEXTCLOUD_GOLDEN_USER="$user" \
    -e NEXTCLOUD_GOLDEN_ROOT="$root_path" \
    -v "$volume:/target:ro" \
    alpine sh -lc '
      root="${NEXTCLOUD_GOLDEN_ROOT#/}"
      test -d "/target/data/${NEXTCLOUD_GOLDEN_USER}/files/${root}"
    ' >/dev/null 2>&1
}

restore_nextcloud_golden_baseline() {
  if [ "$SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE" = "1" ]; then
    echo "SKIP: Nextcloud golden baseline restore disabled by SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE=1"
    return 0
  fi

  local volume
  local archive
  local expected_sha
  local user
  local root_path

  volume="$(get_env_value AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_VOLUME "${PROJECT_NAME}_nextcloud_app")"
  archive="$(get_env_value AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_ARCHIVE "./runtime/ai_decision_studio_functional_baseline/nextcloud_golden_baseline/nextcloud-golden-baseline-v1.tar.gz")"
  expected_sha="$(get_env_value AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_SHA256 "4dd4fb301249fa2ed6e6cc7e223df3beaed2a175b85c352b24ff3ca95636ddb2")"
  user="$(get_env_value AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_USER "$(get_env_value EVIDENCEOPS_NEXTCLOUD_USERNAME danyel)")"
  root_path="$(get_env_value AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_ROOT "$(get_env_value EVIDENCEOPS_NEXTCLOUD_ROOT_PATH /EvidenceOpsDemo)")"

  echo
  echo "== Nextcloud golden baseline check =="
  echo "volume=$volume"
  echo "user=$user"
  echo "root_path=$root_path"

  if volume_has_nextcloud_golden_baseline "$volume" "$user" "$root_path"; then
    echo "OK: Nextcloud golden baseline already present in Docker volume."
    return 0
  fi

  if compose_project_has_running_containers; then
    echo "WARN: compose project has running containers, stopping before restoring Nextcloud volume."
    compose down --remove-orphans
  fi

  if [ ! -f "$archive" ]; then
    echo "ERROR: Nextcloud golden baseline is missing from the Docker volume and archive was not found:" >&2
    echo "  $archive" >&2
    echo "Expected external runtime artifact, not committed to Git." >&2
    exit 1
  fi

  require_command shasum

  local actual_sha
  actual_sha="$(shasum -a 256 "$archive" | awk '{print $1}')"
  echo "archive=$archive"
  echo "actual_sha=$actual_sha"

  if [ "$actual_sha" != "$expected_sha" ]; then
    echo "ERROR: Nextcloud golden baseline SHA mismatch." >&2
    echo "expected_sha=$expected_sha" >&2
    echo "actual_sha=$actual_sha" >&2
    exit 1
  fi

  local archive_dir
  local archive_name
  archive_dir="$(cd "$(dirname "$archive")" && pwd -P)"
  archive_name="$(basename "$archive")"

  echo "Restoring Nextcloud golden baseline into volume $volume ..."

  docker run --rm \
    -e NEXTCLOUD_GOLDEN_USER="$user" \
    -e NEXTCLOUD_GOLDEN_ROOT="$root_path" \
    -v "$volume:/target" \
    -v "$archive_dir:/golden:ro" \
    alpine sh -lc '
      set -e
      find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} +
      tar -xzf "/golden/'"$archive_name"'" -C /target
      root="${NEXTCLOUD_GOLDEN_ROOT#/}"
      test -d "/target/data/${NEXTCLOUD_GOLDEN_USER}/files/${root}"
      echo "OK: restored /target/data/${NEXTCLOUD_GOLDEN_USER}/files/${root}"
    '

  echo "OK: Nextcloud golden baseline restored."
}

ai_lab_golden_state_present() {
  local data_root="$1"

  test -s "${data_root%/}/baseline/.phase95_evidenceops_actions.sqlite3" &&
    test -d "${data_root%/}/baseline/benchmark_runs" &&
    test -s "${data_root%/}/runtime/evals/phase8/phase8_eval_runs.sqlite3" &&
    test -s "${data_root%/}/runtime/logs/product/workflow_history.json"
}

write_ai_lab_golden_state_marker() {
  local marker="$1"
  local archive="$2"
  local sha="$3"

  mkdir -p "$(dirname "$marker")"
  {
    echo "archive=$archive"
    echo "sha256=$sha"
    date -u +"restored_utc=%Y-%m-%dT%H:%M:%SZ"
  } > "$marker"
}

restore_ai_lab_golden_state() {
  if [ "$SKIP_AI_LAB_GOLDEN_STATE_RESTORE" = "1" ]; then
    echo "SKIP: AI Lab golden state restore disabled by SKIP_AI_LAB_GOLDEN_STATE_RESTORE=1"
    return 0
  fi

  local data_root
  local archive
  local expected_sha
  local marker_rel
  local marker
  local tmp

  data_root="$(get_env_value AI_DECISION_STUDIO_ORACLE_DATA_ROOT "$(get_env_value AI_DECISION_STUDIO_DATA_ROOT "./runtime/ai_decision_studio_functional_baseline/oracle_like_data")")"
  archive="$(get_env_value AI_DECISION_STUDIO_AI_LAB_GOLDEN_STATE_ARCHIVE "./runtime/ai_decision_studio_functional_baseline/ai_lab_golden_state/ai-lab-golden-state-v1.tar.gz")"
  expected_sha="$(get_env_value AI_DECISION_STUDIO_AI_LAB_GOLDEN_STATE_SHA256 "c89628335dd1e6a9b9e177d202ab6492361d8b759bb22b41453ed0bc00253a5c")"
  marker_rel="$(get_env_value AI_DECISION_STUDIO_AI_LAB_GOLDEN_STATE_MARKER "runtime/cache/lab/.ai_lab_golden_state_v1_restored")"
  marker="${data_root%/}/${marker_rel}"
  tmp="/tmp/ads_ai_lab_golden_state_restore_${PROJECT_NAME}_$$"

  echo
  echo "== AI Lab golden state check =="
  echo "data_root=$data_root"
  echo "marker=$marker"

  if [ -f "$marker" ]; then
    echo "OK: AI Lab golden state marker already present."
    return 0
  fi

  if ai_lab_golden_state_present "$data_root"; then
    echo "OK: AI Lab golden state already present; repairing marker without overlay."
    write_ai_lab_golden_state_marker "$marker" "$archive" "$expected_sha"
    return 0
  fi

  if compose_project_has_running_containers; then
    echo "WARN: compose project has running containers, stopping before restoring AI Lab golden state."
    compose down --remove-orphans
  fi

  if [ ! -f "$archive" ]; then
    echo "ERROR: AI Lab golden state marker is missing and archive was not found:" >&2
    echo "  $archive" >&2
    echo "Expected external runtime artifact, not committed to Git." >&2
    exit 1
  fi

  require_command shasum
  require_command rsync

  local actual_sha
  actual_sha="$(shasum -a 256 "$archive" | awk '{print $1}')"
  echo "archive=$archive"
  echo "actual_sha=$actual_sha"

  if [ "$actual_sha" != "$expected_sha" ]; then
    echo "ERROR: AI Lab golden state SHA mismatch." >&2
    echo "expected_sha=$expected_sha" >&2
    echo "actual_sha=$actual_sha" >&2
    exit 1
  fi

  echo "Restoring AI Lab golden state into data root ..."

  rm -rf "$tmp"
  mkdir -p "$tmp"
  mkdir -p "$data_root"
  tar -xzf "$archive" -C "$tmp"
  rsync -a "$tmp"/ "$data_root"/
  rm -rf "$tmp"

  rm -f "${data_root%/}/runtime/cache/lab/evidenceops_payload.json" || true

  write_ai_lab_golden_state_marker "$marker" "$archive" "$actual_sha"

  echo "OK: AI Lab golden state restored."
}

if [ "$DOWN_ONLY" = "true" ]; then
  echo "== Local Docker down =="
  echo "env_file=$ENV_FILE"
  echo "project_name=$PROJECT_NAME"
  compose down --remove-orphans
  echo "OK: local Docker stack stopped without removing volumes."
  exit 0
fi

CFG="/tmp/ads_local_docker_compose_$(date +%Y%m%d_%H%M%S).yml"

compose config > "$CFG"

grep -q 'image: ai-decision-studio-product-api:local' "$CFG"
grep -q 'image: ai-decision-studio-frontend:local' "$CFG"
grep -q 'image: ai-decision-studio-ppt-creator:local' "$CFG"
grep -q 'image: ollama/ollama' "$CFG"
grep -q 'image: nextcloud:29-apache' "$CFG"
grep -q 'APP_USERS_ROOT: /app/users' "$CFG"
grep -q 'OLLAMA_BASE_URL: http://ollama:11434/v1' "$CFG"
grep -q 'PRESENTATION_EXPORT_BASE_URL: http://ppt-creator:8787' "$CFG"
grep -q 'EVIDENCEOPS_NEXTCLOUD_BASE_URL: http://nextcloud/remote.php/dav/files/' "$CFG"
grep -q 'EVIDENCEOPS_NEXTCLOUD_ROOT_PATH: /EvidenceOpsDemo' "$CFG"
grep -q 'proxy_pass http://product-api:8011' frontend/nginx.docker.conf

if [ "$CONFIG_ONLY" = "true" ]; then
  echo "OK: local Docker compose config rendered: $CFG"
  exit 0
fi

restore_nextcloud_golden_baseline
restore_ai_lab_golden_state

FRONTEND_BIND_HOST="$(get_env_value AI_DECISION_STUDIO_FRONTEND_BIND_HOST 127.0.0.1)"
FRONTEND_PUBLIC_PORT="$(get_env_value AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT 8071)"
BASE_URL="http://${FRONTEND_BIND_HOST}:${FRONTEND_PUBLIC_PORT}"

echo "== Local Docker up =="
echo "env_file=$ENV_FILE"
echo "project_name=$PROJECT_NAME"
echo "base_url=$BASE_URL"
echo "compose_config=$CFG"

if [ "$NO_BUILD" = "true" ]; then
  compose up -d
else
  compose up -d --build
fi

compose ps

require_command curl

echo
echo "== Waiting for frontend/API through Docker Nginx =="
for i in $(seq 1 120); do
  if curl -fsS "$BASE_URL/health" >/tmp/ads_local_docker_health.json 2>/dev/null; then
    echo "Health OK after ${i}s"
    cat /tmp/ads_local_docker_health.json
    echo
    echo "Local Docker is running:"
    echo "  Frontend/API: $BASE_URL"
    echo "  Health:       $BASE_URL/health"
    echo "  Logs:"
    echo "    docker compose --env-file $ENV_FILE -p $PROJECT_NAME -f docker-compose.local.yml logs -f"
    exit 0
  fi

  sleep 1
done

echo "ERROR: local Docker stack did not become healthy through $BASE_URL/health" >&2
echo
echo "== compose ps =="
compose ps || true
echo
echo "== frontend logs =="
compose logs --tail=160 frontend || true
echo
echo "== product-api logs =="
compose logs --tail=160 product-api || true
exit 1
BASH

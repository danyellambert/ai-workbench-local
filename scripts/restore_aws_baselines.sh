#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-${ENV_FILE:-.env.aws}}"
COMPOSE_FILE="${AI_DECISION_STUDIO_AWS_COMPOSE_FILE:-docker-compose.aws.yml}"
PROJECT="${AI_DECISION_STUDIO_DOCKER_PROJECT:-ai-decision-studio}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "ERROR: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

run_sudo() {
  if [ "$(id -u)" = "0" ]; then
    "$@"
  else
    sudo "$@"
  fi
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

ensure_archive_available() {
  local archive="$1"
  local fallback="/tmp/$(basename "$archive")"

  if [ ! -f "$archive" ]; then
    if [ -f "$fallback" ]; then
      echo "archive_missing_at=$archive"
      echo "using_tmp_fallback=$fallback"
      run_sudo mkdir -p "$(dirname "$archive")"
      run_sudo cp "$fallback" "$archive"
    fi
  fi

  if [ -f "$archive" ]; then
    # Archives copied into /opt may have been created by sudo. Make them
    # readable by the deploy user before SHA validation and later cleanup.
    run_sudo chown "$(id -u):$(id -g)" "$archive" || true
    run_sudo chmod 600 "$archive" || true
  fi
}

verify_archive() {
  local label="$1"
  local archive="$2"
  local expected_sha="$3"

  if [ ! -f "$archive" ]; then
    echo "ERROR: missing $label archive: $archive" >&2
    exit 1
  fi

  if [ -n "$expected_sha" ]; then
    local actual_sha
    actual_sha="$(sha256_file "$archive")"
    echo "$label sha256=$actual_sha"

    if [ "$actual_sha" != "$expected_sha" ]; then
      echo "ERROR: $label sha mismatch" >&2
      echo "expected=$expected_sha" >&2
      echo "actual=$actual_sha" >&2
      exit 1
    fi
  else
    echo "WARN: no expected sha configured for $label"
  fi
}

wait_for_service() {
  local service="$1"

  for _ in $(seq 1 60); do
    local cid
    cid="$(docker compose -p "$PROJECT" -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null || true)"

    if [ -n "$cid" ]; then
      local health
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
      echo "$service health=$health"

      if [ "$health" = "healthy" ] || [ "$health" = "running" ]; then
        return 0
      fi
    fi

    sleep 3
  done

  echo "ERROR: service did not become healthy/running: $service" >&2
  exit 1
}

guard_data_root() {
  local data_root="$1"

  if [ "$data_root" != "/opt/ai-decision-studio/data" ]; then
    echo "ERROR: refusing to modify unexpected data root: $data_root" >&2
    exit 1
  fi
}

nextcloud_baseline_present() {
  local volume="$1"
  local user="$2"
  local root_path="$3"

  docker volume inspect "$volume" >/dev/null 2>&1 || return 1

  docker run --rm \
    -v "$volume:/target:ro" \
    alpine sh -lc '
      user="$1"
      root_path="${2#/}"
      test -d "/target/data/${user}/files/${root_path}"
    ' sh "$user" "$root_path" >/dev/null 2>&1
}

product_data_baseline_present() {
  local data_root="$1"

  [ -d "$data_root/baseline" ] || return 1
  [ -d "$data_root/runtime" ] || return 1
  [ -d "$data_root/users" ] || return 1
  [ -d "$data_root/artifacts" ] || return 1

  local baseline_files
  local runtime_files
  local artifacts_files

  baseline_files="$(find "$data_root/baseline" -type f 2>/dev/null | wc -l | tr -d ' ')"
  runtime_files="$(find "$data_root/runtime" -type f 2>/dev/null | wc -l | tr -d ' ')"
  artifacts_files="$(find "$data_root/artifacts" -type f 2>/dev/null | wc -l | tr -d ' ')"

  [ "$baseline_files" -gt 100 ] || return 1
  [ "$runtime_files" -gt 10 ] || return 1
  [ "$artifacts_files" -gt 10 ] || return 1
}

restore_nextcloud_baseline() {
  local volume="$1"
  local archive="$2"
  local expected_sha="$3"
  local user="$4"
  local password="$5"
  local root_path="$6"

  ensure_archive_available "$archive"
  verify_archive "nextcloud_golden_baseline" "$archive" "$expected_sha"

  echo
  echo "== restore Nextcloud golden baseline =="
  echo "volume=$volume"
  echo "user=$user"
  echo "root_path=$root_path"

  docker volume create "$volume" >/dev/null

  docker run --rm \
    -v "$volume:/target" \
    -v "$(dirname "$archive"):/golden:ro" \
    alpine sh -lc '
      archive_name="$1"
      user="$2"
      root_path="${3#/}"

      rm -rf /target/* /target/.[!.]* /target/..?* 2>/dev/null || true
      tar -xzf "/golden/${archive_name}" -C /target
      test -d "/target/data/${user}/files/${root_path}"
      echo "OK: Nextcloud golden baseline restored"
    ' sh "$(basename "$archive")" "$user" "$root_path"

  echo
  echo "== start Nextcloud and align restored user =="
  docker compose --env-file "$ENV_FILE" -p "$PROJECT" -f "$COMPOSE_FILE" up -d nextcloud
  wait_for_service nextcloud

  if [ -n "$password" ]; then
    docker compose --env-file "$ENV_FILE" -p "$PROJECT" -f "$COMPOSE_FILE" exec -T \
      -e OC_PASS="$password" \
      --user www-data \
      nextcloud php occ user:resetpassword --password-from-env "$user"
  else
    echo "WARN: Nextcloud password empty; skipping password reset"
  fi

  local idx=1
  for domain in localhost 127.0.0.1 nextcloud; do
    docker compose --env-file "$ENV_FILE" -p "$PROJECT" -f "$COMPOSE_FILE" exec -T \
      --user www-data \
      nextcloud php occ config:system:set trusted_domains "$idx" --value="$domain"
    idx=$((idx + 1))
  done
}

restore_product_data_baseline() {
  local data_root="$1"
  local archive="$2"
  local expected_sha="$3"
  local owner="$4"

  guard_data_root "$data_root"
  ensure_archive_available "$archive"
  verify_archive "product_data_baseline" "$archive" "$expected_sha"

  echo
  echo "== restore Axiovance product data baseline =="
  echo "data_root=$data_root"
  echo "owner=$owner"

  run_sudo mkdir -p "$data_root"
  run_sudo chown "$owner" "$data_root"
  run_sudo chmod u+rwx "$data_root"

  run_sudo rm -rf \
    "$data_root/baseline" \
    "$data_root/runtime" \
    "$data_root/users" \
    "$data_root/artifacts"

  tar -xzf "$archive" -C "$data_root"

  run_sudo chown -R "$owner" \
    "$data_root/baseline" \
    "$data_root/runtime" \
    "$data_root/users" \
    "$data_root/artifacts"

  chmod -R u+rwX,go+rX \
    "$data_root/baseline" \
    "$data_root/runtime" \
    "$data_root/users" \
    "$data_root/artifacts"

  for d in baseline runtime users artifacts; do
    echo "$d files=$(find "$data_root/$d" -type f | wc -l | tr -d ' ')"
    du -sh "$data_root/$d" || true
  done
}

DATA_ROOT="${AI_DECISION_STUDIO_DATA_ROOT:-/opt/ai-decision-studio/data}"

NEXTCLOUD_RESTORE="${AI_DECISION_STUDIO_RESTORE_NEXTCLOUD_GOLDEN_BASELINE:-1}"
NEXTCLOUD_FORCE="${AI_DECISION_STUDIO_FORCE_RESTORE_NEXTCLOUD_GOLDEN_BASELINE:-0}"
NEXTCLOUD_VOLUME="${AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_VOLUME:-${PROJECT}_nextcloud_app}"
NEXTCLOUD_ARCHIVE="${AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_ARCHIVE:-/opt/ai-decision-studio/golden_baseline/nextcloud-golden-baseline-v1.tar.gz}"
NEXTCLOUD_SHA="${AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_SHA256:-4dd4fb301249fa2ed6e6cc7e223df3beaed2a175b85c352b24ff3ca95636ddb2}"
NEXTCLOUD_USER="${NEXTCLOUD_ADMIN_USER:-${EVIDENCEOPS_NEXTCLOUD_USERNAME:-danyel}}"
NEXTCLOUD_PASSWORD="${NEXTCLOUD_ADMIN_PASSWORD:-${EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD:-}}"
NEXTCLOUD_ROOT="${EVIDENCEOPS_NEXTCLOUD_ROOT_PATH:-/EvidenceOpsDemo}"

PRODUCT_RESTORE="${AI_DECISION_STUDIO_RESTORE_PRODUCT_DATA_BASELINE:-1}"
PRODUCT_FORCE="${AI_DECISION_STUDIO_FORCE_RESTORE_PRODUCT_DATA_BASELINE:-0}"
PRODUCT_ARCHIVE="${AI_DECISION_STUDIO_PRODUCT_DATA_BASELINE_ARCHIVE:-/opt/ai-decision-studio/baselines/ai-decision-studio-product-data-baseline.tar.gz}"
PRODUCT_SHA="${AI_DECISION_STUDIO_PRODUCT_DATA_BASELINE_SHA256:-c00741554086501c201c260988d1468ccb08f8ecf4fde79129697eb659904e45}"
PRODUCT_OWNER="${AI_DECISION_STUDIO_PRODUCT_DATA_BASELINE_OWNER:-ubuntu:ubuntu}"

echo
echo "== AWS baseline restore preflight =="
echo "env_file=$ENV_FILE"
echo "compose_file=$COMPOSE_FILE"
echo "project=$PROJECT"
echo "data_root=$DATA_ROOT"

NEED_DOWN=0

if truthy "$NEXTCLOUD_RESTORE"; then
  if truthy "$NEXTCLOUD_FORCE" || ! nextcloud_baseline_present "$NEXTCLOUD_VOLUME" "$NEXTCLOUD_USER" "$NEXTCLOUD_ROOT"; then
    echo "nextcloud_baseline_restore_needed=1"
    NEED_DOWN=1
  else
    echo "nextcloud_baseline_restore_needed=0"
  fi
else
  echo "nextcloud_baseline_restore_disabled=1"
fi

if truthy "$PRODUCT_RESTORE"; then
  if truthy "$PRODUCT_FORCE" || ! product_data_baseline_present "$DATA_ROOT"; then
    echo "product_data_baseline_restore_needed=1"
    NEED_DOWN=1
  else
    echo "product_data_baseline_restore_needed=0"
  fi
else
  echo "product_data_baseline_restore_disabled=1"
fi

if [ "$NEED_DOWN" = "1" ]; then
  echo
  echo "== stop stack before baseline restore =="
  docker compose --env-file "$ENV_FILE" -p "$PROJECT" -f "$COMPOSE_FILE" down --remove-orphans || true
fi

if truthy "$NEXTCLOUD_RESTORE"; then
  if truthy "$NEXTCLOUD_FORCE" || ! nextcloud_baseline_present "$NEXTCLOUD_VOLUME" "$NEXTCLOUD_USER" "$NEXTCLOUD_ROOT"; then
    restore_nextcloud_baseline "$NEXTCLOUD_VOLUME" "$NEXTCLOUD_ARCHIVE" "$NEXTCLOUD_SHA" "$NEXTCLOUD_USER" "$NEXTCLOUD_PASSWORD" "$NEXTCLOUD_ROOT"
  fi
fi

if truthy "$PRODUCT_RESTORE"; then
  if truthy "$PRODUCT_FORCE" || ! product_data_baseline_present "$DATA_ROOT"; then
    restore_product_data_baseline "$DATA_ROOT" "$PRODUCT_ARCHIVE" "$PRODUCT_SHA" "$PRODUCT_OWNER"
  fi
fi

echo
echo "OK: AWS baseline restore check completed"

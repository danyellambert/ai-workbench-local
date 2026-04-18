#!/usr/bin/env bash
set -euo pipefail

ai_lab_detect_rollup_native_pkg() {
  local platform arch libc
  platform="$(node -p 'process.platform')"
  arch="$(node -p 'process.arch')"
  case "$platform/$arch" in
    darwin/arm64) echo '@rollup/rollup-darwin-arm64' ;;
    darwin/x64) echo '@rollup/rollup-darwin-x64' ;;
    linux/x64)
      libc="$(node -p "process.report && typeof process.report.getReport === 'function' && process.report.getReport().header && process.report.getReport().header.glibcVersionRuntime ? 'gnu' : 'musl'")"
      echo "@rollup/rollup-linux-x64-${libc}"
      ;;
    linux/arm64)
      libc="$(node -p "process.report && typeof process.report.getReport === 'function' && process.report.getReport().header && process.report.getReport().header.glibcVersionRuntime ? 'gnu' : 'musl'")"
      echo "@rollup/rollup-linux-arm64-${libc}"
      ;;
    win32/x64) echo '@rollup/rollup-win32-x64-msvc' ;;
    win32/arm64) echo '@rollup/rollup-win32-arm64-msvc' ;;
    *) echo '' ;;
  esac
}

ensure_rollup_native() {
  local repo_root="${1:?repo root required}"
  local frontend_dir="$repo_root/frontend"
  local rollup_pkg rollup_dir

  if [ ! -f "$frontend_dir/package.json" ]; then
    return 0
  fi

  if [ ! -d "$frontend_dir/node_modules" ]; then
    echo "[ai-lab] frontend node_modules missing; running npm install..."
    (cd "$frontend_dir" && npm install)
  fi

  rollup_pkg="$(ai_lab_detect_rollup_native_pkg)"
  if [ -z "$rollup_pkg" ]; then
    return 0
  fi

  rollup_dir="$frontend_dir/node_modules/@rollup/${rollup_pkg#@rollup/}"
  if [ -d "$rollup_dir" ]; then
    return 0
  fi

  echo "[ai-lab] installing missing Rollup native package: $rollup_pkg"
  (cd "$frontend_dir" && npm install -D "$rollup_pkg")
}

ai_lab_port_in_use() {
  local port="${1:?port required}"
  python - <<'PY' "$port"
import socket, sys
port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.5)
    sys.exit(0 if sock.connect_ex(('127.0.0.1', port)) == 0 else 1)
PY
}

ai_lab_find_free_port() {
  python - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PY
}

ai_lab_choose_port() {
  local preferred="${1:?preferred port required}"
  local reuse_existing="${2:-0}"
  if [ "$reuse_existing" = "1" ]; then
    echo "$preferred"
    return 0
  fi
  if ai_lab_port_in_use "$preferred"; then
    ai_lab_find_free_port
  else
    echo "$preferred"
  fi
}

reset_ai_lab_output_dir() {
  local out_dir="${1:?output dir required}"
  rm -rf "$out_dir"
  mkdir -p "$out_dir"
}

write_ai_lab_run_meta() {
  local out_dir="${1:?output dir required}"
  local command_line="${2:-}"
  mkdir -p "$out_dir"
  python - <<'PY' "$out_dir" "$command_line"
import json, os, sys, time
out_dir = sys.argv[1]
command_line = sys.argv[2]
payload = {
    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'pid': os.getpid(),
    'cwd': os.getcwd(),
    'command': command_line,
}
with open(os.path.join(out_dir, 'run-meta.json'), 'w', encoding='utf-8') as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
PY
}

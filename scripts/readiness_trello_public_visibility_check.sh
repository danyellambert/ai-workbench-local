#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.aws}"
PROBE_CARD_COUNT="${PROBE_CARD_COUNT:-3}"

usage() {
  cat <<'USAGE'
Usage:
  ENV_FILE=.env.aws scripts/readiness_trello_public_visibility_check.sh

Optional env:
  ENV_FILE
  PROBE_CARD_COUNT

This check:
  - reads Trello credentials from the env file without printing secrets;
  - verifies the configured board permissionLevel is public;
  - probes the board/card URLs anonymously, without key/token;
  - fails if Trello appears to require login or if the board is not public.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?missing value for --env-file}"
      shift 2
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
  exit 1
fi

echo "== Trello public visibility readiness =="
echo "env_file=$ENV_FILE"

ENV_FILE="$ENV_FILE" PROBE_CARD_COUNT="$PROBE_CARD_COUNT" python3 - <<'PY'
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


def parse_env(path: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


env_file = os.environ["ENV_FILE"]
probe_count = int(os.environ.get("PROBE_CARD_COUNT", "3"))

env = parse_env(env_file)

required = [
    "EVIDENCEOPS_TRELLO_API_KEY",
    "EVIDENCEOPS_TRELLO_TOKEN",
    "EVIDENCEOPS_TRELLO_BOARD_ID",
]
missing = [key for key in required if not env.get(key)]
if missing:
    raise SystemExit(f"ERROR: Trello env is incomplete: {missing}")

key = env["EVIDENCEOPS_TRELLO_API_KEY"]
token = env["EVIDENCEOPS_TRELLO_TOKEN"]
board_id = env["EVIDENCEOPS_TRELLO_BOARD_ID"]

params = urllib.parse.urlencode({
    "key": key,
    "token": token,
    "fields": "name,url,shortUrl,prefs,closed",
    "cards": "open",
    "card_fields": "name,url,shortUrl",
})
api_url = f"https://api.trello.com/1/boards/{urllib.parse.quote(board_id)}?{params}"

with urllib.request.urlopen(api_url, timeout=30) as response:
    board = json.loads(response.read().decode("utf-8"))

prefs = board.get("prefs") or {}
permission = prefs.get("permissionLevel")

safe_board = {
    "board_id": board_id,
    "name": board.get("name"),
    "closed": board.get("closed"),
    "permissionLevel": permission,
    "url": board.get("url"),
    "shortUrl": board.get("shortUrl"),
    "open_card_count": len(board.get("cards") or []),
}

print(json.dumps({"board": safe_board}, indent=2, sort_keys=True))

if permission != "public":
    raise SystemExit(f"ERROR: Trello board is not public. permissionLevel={permission!r}")

targets: list[tuple[str, str]] = []
board_url = board.get("url") or board.get("shortUrl")
if board_url:
    targets.append(("board", str(board_url)))

for card in (board.get("cards") or [])[:probe_count]:
    card_url = card.get("url") or card.get("shortUrl")
    if card_url:
        targets.append((f"card: {card.get('name')}", str(card_url)))

if not targets:
    raise SystemExit("ERROR: no Trello board/card URLs available for anonymous probe")

probe_results = []

for label, target in targets:
    result = subprocess.run(
        [
            "curl",
            "-L",
            "-sS",
            "-o",
            "/tmp/ads_trello_public_probe.html",
            "-w",
            "%{http_code} %{url_effective}",
            target,
        ],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    body = Path("/tmp/ads_trello_public_probe.html").read_text(encoding="utf-8", errors="replace")[:8000]
    title_match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I | re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
    login_like = bool(re.search(r"log in|sign in|login|atlassian account", body, flags=re.I))

    http_text = result.stdout.strip()
    status = http_text.split(" ", 1)[0] if http_text else ""

    item = {
        "label": label,
        "http": http_text,
        "title": title[:160],
        "login_like_page": login_like,
    }
    probe_results.append(item)

    if status != "200":
        raise SystemExit(f"ERROR: anonymous Trello probe failed for {label}: {http_text}")
    if login_like:
        raise SystemExit(f"ERROR: anonymous Trello probe appears login-gated for {label}")

print(json.dumps({"anonymous_probes": probe_results}, indent=2, sort_keys=True))
print("OK: Trello board is public and anonymous probes passed.")
PY

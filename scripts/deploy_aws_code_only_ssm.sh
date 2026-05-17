#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"

if [ "$MODE" != "--dry-run" ] && [ "$MODE" != "--execute" ]; then
  echo "Usage: $0 --dry-run|--execute" >&2
  exit 2
fi

AWS_REGION="${AWS_REGION:?AWS_REGION is required}"
AWS_EC2_INSTANCE_ID="${AWS_EC2_INSTANCE_ID:?AWS_EC2_INSTANCE_ID is required}"
AWS_DEPLOY_APP_DIR="${AWS_DEPLOY_APP_DIR:?AWS_DEPLOY_APP_DIR is required}"
REPO="${REPO:-danyellambert/ai-workbench-local}"
DEPLOY_SHA="${DEPLOY_SHA:-$(git rev-parse HEAD)}"
SSM_DEPLOY_VERBOSE="${SSM_DEPLOY_VERBOSE:-0}"

REMOTE_SCRIPT="/tmp/axiovance_ssm_deploy_${DEPLOY_SHA:0:12}.sh"
REMOTE_SCRIPT_URL="https://raw.githubusercontent.com/${REPO}/${DEPLOY_SHA}/scripts/deploy_aws_code_only_ssm_remote.sh"

echo "== SSM deploy driver =="
echo "mode=$MODE"
echo "region=$AWS_REGION"
echo "instance=$AWS_EC2_INSTANCE_ID"
echo "app_dir=$AWS_DEPLOY_APP_DIR"
echo "repo=$REPO"
echo "deploy_sha=$DEPLOY_SHA"
echo "remote_script_url=$REMOTE_SCRIPT_URL"

PAYLOAD="$(mktemp)"

python3 - <<PY > "$PAYLOAD"
import json
import shlex

instance_id = "$AWS_EC2_INSTANCE_ID"
repo = "$REPO"
deploy_sha = "$DEPLOY_SHA"
app_dir = "$AWS_DEPLOY_APP_DIR"
mode = "$MODE"
ssm_deploy_verbose = "$SSM_DEPLOY_VERBOSE"
remote_script = "$REMOTE_SCRIPT"
remote_script_url = "$REMOTE_SCRIPT_URL"

remote_body = f'''
set -euo pipefail

echo "Downloading SSM remote deploy script"
curl -fsSL "{remote_script_url}" -o "{remote_script}"
chmod 700 "{remote_script}"

echo "Running SSM remote deploy script"
REPO="{repo}" \\
DEPLOY_SHA="{deploy_sha}" \\
APP_DIR="{app_dir}" \\
SSM_DEPLOY_VERBOSE="{ssm_deploy_verbose}" \\
bash "{remote_script}" "{mode}"
'''.strip()

command = "bash -lc " + shlex.quote(remote_body)

payload = {
    "InstanceIds": [instance_id],
    "DocumentName": "AWS-RunShellScript",
    "Comment": f"Axiovance SSM code-only deploy {deploy_sha[:12]} {mode}",
    "Parameters": {
        "commands": [command]
    }
}

print(json.dumps(payload))
PY

COMMAND_ID="$(
  aws ssm send-command \
    --region "$AWS_REGION" \
    --cli-input-json "file://$PAYLOAD" \
    --query "Command.CommandId" \
    --output text
)"

rm -f "$PAYLOAD"

echo "SSM command id: $COMMAND_ID"

for attempt in $(seq 1 120); do
  STATUS="$(
    aws ssm get-command-invocation \
      --region "$AWS_REGION" \
      --command-id "$COMMAND_ID" \
      --instance-id "$AWS_EC2_INSTANCE_ID" \
      --query "Status" \
      --output text 2>/dev/null || true
  )"

  echo "attempt=$attempt status=$STATUS"

  case "$STATUS" in
    Success)
      echo
      echo "== SSM STDOUT =="
      aws ssm get-command-invocation \
        --region "$AWS_REGION" \
        --command-id "$COMMAND_ID" \
        --instance-id "$AWS_EC2_INSTANCE_ID" \
        --query "StandardOutputContent" \
        --output text || true

      echo
      echo "✅ SSM deploy completed successfully."
      exit 0
      ;;

    Failed|Cancelled|TimedOut|Cancelling)
      echo
      echo "== SSM STDOUT =="
      aws ssm get-command-invocation \
        --region "$AWS_REGION" \
        --command-id "$COMMAND_ID" \
        --instance-id "$AWS_EC2_INSTANCE_ID" \
        --query "StandardOutputContent" \
        --output text || true

      echo
      echo "== SSM STDERR =="
      aws ssm get-command-invocation \
        --region "$AWS_REGION" \
        --command-id "$COMMAND_ID" \
        --instance-id "$AWS_EC2_INSTANCE_ID" \
        --query "StandardErrorContent" \
        --output text || true

      echo "ERROR: SSM deploy failed with status: $STATUS" >&2
      exit 1
      ;;
  esac

  sleep 10
done

echo "ERROR: SSM deploy did not finish in time." >&2
exit 1

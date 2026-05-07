# Public demo anti-abuse hardening

This hardening layer protects only anonymous public demo sessions.

It must not mutate:

~~~text
baseline
runtime global state
global artifacts
admin/global workspace
Nextcloud golden baseline archive
product data baseline archive
~~~

It may only remove or limit data under:

~~~text
/app/users/public_sessions/{session_id}/overlay
/opt/ai-decision-studio/data/users/public_sessions/{session_id}/overlay
~~~

## Enabled controls in this block

~~~text
TTL for old public sessions
cleanup for expired public session overlays
minimal disk/container/health monitoring
~~~

## Environment

~~~env
AI_DECISION_STUDIO_PUBLIC_ABUSE_LIMITS_ENABLED=true
AI_DECISION_STUDIO_PUBLIC_CLEANUP_ENABLED=1
AI_DECISION_STUDIO_PUBLIC_SESSION_TTL_HOURS=48
AI_DECISION_STUDIO_PUBLIC_OVERLAY_RETENTION_HOURS=48
AI_DECISION_STUDIO_PUBLIC_CLEANUP_DRY_RUN=0
AI_DECISION_STUDIO_PUBLIC_CLEANUP_USE_SUDO=1
AI_DECISION_STUDIO_DISK_WARN_PERCENT=85
AI_DECISION_STUDIO_DISK_FAIL_PERCENT=95
~~~

## Cleanup dry run

~~~bash
AI_DECISION_STUDIO_DATA_ROOT=/opt/ai-decision-studio/data \
scripts/cleanup_public_demo_sessions.py --dry-run
~~~

## Cleanup apply

~~~bash
AI_DECISION_STUDIO_DATA_ROOT=/opt/ai-decision-studio/data \
scripts/cleanup_public_demo_sessions.py --ttl-hours 48 --apply
~~~

## Minimal monitoring

~~~bash
BASE_URL=http://127.0.0.1:8071 \
scripts/monitor_aws_minimal_health.sh
~~~

## Safety rule

The cleanup script must only delete direct children matching:

~~~text
/users/public_sessions/sess_*
~~~

It must refuse to operate on baseline/global paths.

## Not included in this block

Quota and deck-generation rate limits are enforced in API/request code, not by this filesystem cleanup script.

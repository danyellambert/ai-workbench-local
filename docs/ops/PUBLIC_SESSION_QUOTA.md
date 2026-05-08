# Public session quota

This control limits the size of each anonymous public demo session overlay.

It does not implement TTL, automatic overlay cleanup, deck generation rate limiting, upload/import size limits, monitoring, backup automation, or infrastructure access changes.

## Scope

The quota applies only to public sessions:

    /app/users/public_sessions/{session_id}/overlay
    /opt/ai-decision-studio/data/users/public_sessions/{session_id}/overlay

Admin/global requests bypass this quota.

The quota must not inspect, delete, or mutate baseline, runtime global state, global artifacts, Nextcloud golden baseline, or product data baseline.

## Environment

    AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB=250

Set to 0 to disable public session quota enforcement.

## Behavior

Public session below limit is allowed.
Public session over limit receives HTTP 429 for protected public mutations.
Admin/global request is not limited by this control.

## Relationship to deck rate limit

Public session quota limits overlay storage size.
Deck rate limit limits POST /api/product/generate-deck frequency by session/IP.

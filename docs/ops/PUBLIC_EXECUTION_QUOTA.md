# Public execution quota

This control limits how many execution attempts an anonymous public session can make within a rolling time window.

Covered public execution endpoints:

    POST /api/product/run-workflow
    POST /api/lab/workflow-inspector/run
    POST /api/lab/chat/sessions/{sessionId}/messages

Default public demo policy:

    AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_ENABLED=true
    AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_MAX_PER_SESSION=4
    AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_WINDOW_SECONDS=1200

1200 seconds equals 20 minutes.

Admin/global requests bypass this quota.

When the quota is exceeded, the backend returns HTTP 429 with:

    execution_quota.retry_after_seconds
    execution_quota.reset_at
    execution_quota.window_seconds
    execution_quota.max_per_session

The frontend should stop loading and show a clear user-facing message instead of silently hanging.

This control does not delete data and does not change baseline/global state. It writes only a small rolling-window counter file under the users root:

    /app/users/public_execution_quota/executions.json
    /opt/ai-decision-studio/data/users/public_execution_quota/executions.json

Set max per session to 0 to disable enforcement.

This is separate from the deck-generation rate limiter.

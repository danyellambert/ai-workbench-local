# Public execution quota

This control limits how many execution attempts an anonymous public session can make.

It applies to public execution endpoints such as:

    POST /api/product/run-workflow
    POST /api/lab/workflow-inspector/run
    POST /api/lab/chat/sessions/{sessionId}/messages

Admin/global requests bypass this quota.

This control does not delete data and does not change baseline/global state. It writes only a small counter file under the users root:

    /app/users/public_execution_quota/executions.json
    /opt/ai-decision-studio/data/users/public_execution_quota/executions.json

Environment:

    AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_ENABLED=true
    AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_MAX_PER_SESSION=20

Set max per session to 0 to disable enforcement.

Document Experiments is implemented by the AI Lab chat message endpoint and is covered by this quota.

This is separate from the deck-generation rate limiter.

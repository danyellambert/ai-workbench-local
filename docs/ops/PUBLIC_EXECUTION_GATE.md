# Public execution in-flight gate

This control limits simultaneous public executions so one visitor cannot consume the shared AI runtime/API key from multiple browser tabs at the same time.

It is separate from the rolling execution quota.

Covered public execution endpoints:

    POST /api/product/run-workflow
    POST /api/lab/workflow-inspector/run
    POST /api/lab/chat/sessions/{sessionId}/messages

Default policy:

    AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_ENABLED=true
    AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_PER_SESSION=1
    AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_GLOBAL=2
    AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_TTL_SECONDS=300

Behavior:

- Admin/global requests bypass this gate.
- A public session can have only one workflow/chat execution in progress.
- The public demo as a whole can have only a small number of executions in progress.
- If a session already has a run in progress, the backend returns HTTP 429 with `execution_gate`.
- If the public demo runtime is globally busy, the backend returns HTTP 429 with `execution_gate`.
- The frontend shows a clear message instead of leaving the run button/loading state stuck.

State file:

    /app/users/public_execution_gate/in_flight.json
    /opt/ai-decision-studio/data/users/public_execution_gate/in_flight.json

The TTL only removes stale in-flight markers for crashed/interrupted executions. It does not delete user overlay data, documents, run history, artifacts, or baseline/global state.

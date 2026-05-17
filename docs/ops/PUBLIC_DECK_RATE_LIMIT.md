# Public deck generation rate limit

This control only protects deck generation:

~~~text
POST /api/product/generate-deck
~~~

It does not implement:

~~~text
public session TTL
automatic overlay cleanup
general public session quota
upload/import size limits
backup/restore automation
infrastructure access changes
~~~

## Scope

Admin/global requests bypass this limiter.

Public demo requests are limited by:

~~~text
anonymous public session id
client IP hash
~~~

The limiter state is stored under the users root:

~~~text
/app/users/public_rate_limits/deck_generation.json
/opt/ai-decision-studio/data/users/public_rate_limits/deck_generation.json
~~~

It must not write to:

~~~text
baseline
runtime global state
global artifacts
Nextcloud golden baseline
product data baseline
~~~

## Environment

~~~env
AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_ENABLED=true
AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_WINDOW_SECONDS=3600
AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_MAX_PER_SESSION=3
AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_MAX_PER_IP=12
~~~

## Expected behavior

~~~text
Public visitor within limit -> deck generation proceeds.
Public visitor over limit -> HTTP 429.
Admin -> not limited by this control.
~~~

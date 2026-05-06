# Oracle deploy assets

This directory preserves Oracle-specific host-level deployment assets.

These files are not part of the current AWS slim deployment path.

Current AWS deployment uses the generic deployment bundle, `.env.aws`, `docker-compose.oracle-like.yml`, `docker-compose.aws-slim.override.yml`, `scripts/deploy_aws_slim.sh`, and `scripts/smoke_aws_slim.sh`.

`Caddyfile.example` is retained here as a historical/deferred Oracle Always Free reverse-proxy template.

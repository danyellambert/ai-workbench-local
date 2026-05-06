# Oracle Always Free — Security Exposure Checklist

Use this checklist before exposing AI Decision Studio publicly.

## Public DNS

- [ ] Domain or subdomain selected.
- [ ] DNS A record points to the Oracle VM public IPv4.
- [ ] AI_DECISION_STUDIO_PUBLIC_DOMAIN matches the DNS name.
- [ ] AI_DECISION_STUDIO_ACME_EMAIL is set for Let's Encrypt/ACME.

## Reverse proxy / HTTPS

- [ ] Caddy or Nginx is installed on the VM host.
- [ ] Caddy/Nginx is the only service exposed on 80/tcp and 443/tcp.
- [ ] TLS certificate is issued successfully.
- [ ] HTTP redirects to HTTPS.
- [ ] Frontend container is reachable only from localhost: 127.0.0.1:8080.
- [ ] Product API is reachable only inside Docker private network.

Recommended Caddy template:

    deploy/oracle/Caddyfile.example

## OCI firewall / NSG / Security List

Public ingress allowed:

- [ ] 80/tcp from 0.0.0.0/0
- [ ] 443/tcp from 0.0.0.0/0

Restricted ingress:

- [ ] 22/tcp only from your admin IP, not from 0.0.0.0/0.

Must NOT be public:

- [ ] 8011/tcp product-api
- [ ] 8787/tcp ppt-creator
- [ ] 11434/tcp ollama
- [ ] 8085/tcp nextcloud/local WebDAV
- [ ] 8080/tcp frontend direct port, when reverse proxy is active

## App secrets

- [ ] .env.oracle exists only on the VM.
- [ ] .env.oracle is chmod 600.
- [ ] AI_DECISION_STUDIO_SESSION_SECRET is strong and unique.
- [ ] AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH is set and quoted if it contains $.
- [ ] No real provider keys are committed.
- [ ] scripts/validate_oracle_environment_contract.sh .env.oracle passes.

## Public demo guardrails

- [ ] AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB is set, recommended 100 for public demo.
- [ ] scripts/cleanup_public_session_overlays.py is scheduled by cron/systemd timer.
- [ ] Backups are generated and restore has been tested.
- [ ] Product API returns 429 when a public session exceeds quota.

## Visitor visibility

You can know visits, IPs, paths, user agents, errors and anonymous session ids from reverse proxy logs and app logs.

You cannot honestly know a visitor's real name/email/company unless they log in or voluntarily submit contact information.

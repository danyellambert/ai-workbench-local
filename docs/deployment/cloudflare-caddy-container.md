# Cloudflare + Caddy Container Deployment

Public entrypoint:

    https://aidstudio.danyel-lambert.com

Architecture:

    Cloudflare Free
      -> EC2 ports 80/443
      -> caddy container
      -> frontend:8080
      -> product-api and internal services

Session safety rules:

- Do not enable Cache Everything.
- Bypass cache for /api/*.
- Bypass cache for /health.
- Use Cloudflare SSL/TLS mode Full (strict) after Caddy has a valid origin certificate.
- Keep public session cookies untouched.
- Keep workflow quota and in-flight gates enforced by product-api.
- Keep port 8071 closed publicly after HTTPS is validated.

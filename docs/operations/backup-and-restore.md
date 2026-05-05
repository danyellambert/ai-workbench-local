# Backup and restore

The product has two operational layers:

- application code;
- product data roots.

The application code is versioned in Git. The current Docker/AWS data payload is represented by four roots:

- baseline
- runtime
- artifacts
- users

Local data payload path:

- runtime/ai_decision_studio_functional_baseline/oracle_like_data

AWS data root path:

- /opt/ai-decision-studio/data

What to back up before risky operations:

- baseline
- runtime
- artifacts
- users
- real env files such as .env.docker, .env.aws, or .env.oracle

What not to commit as a normal code change:

- real env files;
- backup archives;
- .DS_Store;
- local generated scratch output;
- unrelated runtime snapshots.

Before changing deploy payload or docs that reference deploy payload:

1. Confirm git status is clean.
2. Create a backup branch.
3. Confirm which paths are mounted by compose.
4. Avoid touching src/product, frontend/src, main_product_api.py, or the versioned payload unless the task explicitly requires it.
5. Validate compose render after the change.
6. Commit small, isolated changes.

Rollback pattern:

- git reset --hard <backup-branch>

For AWS host backups, prefer copying /opt/ai-decision-studio/data to a timestamped backup location before replacing any root.

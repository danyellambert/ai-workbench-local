# Local Backup Register

This file is a sanitized template for documenting local-only backups.

Do not commit:

- private machine paths;
- usernames;
- real `.env` files;
- SSH keys;
- cloud credentials;
- backup archives;
- backup manifests containing private paths or secrets.

Keep real backup paths and generated manifests in an ignored local location such as `runtime/repo_cleanup/` or another private backup directory.

## Backup entry template

Date/time:
Timezone:
Operator:
Branch:
Commit:
Purpose:

Backup type:
- git bundle:
- filesystem snapshot:
- data-root archive:
- database export:
- other:

Local backup location:
<private local path, not committed>

Included:
- repository refs:
- runtime state:
- artifacts:
- baseline/data:
- users/overlays:
- deployment env examples only:

Excluded:
- real .env files:
- secrets:
- cloud credentials:
- node_modules / virtualenvs:
- generated caches:
- private absolute paths:

Verification:
- archive exists:
- manifest reviewed:
- restore tested:
- no secrets found:
- no private paths committed:

Restore notes:
<commands or private notes kept outside the public repository>

## Recommended storage

Store real backup registers and manifests outside Git, for example:

- `runtime/repo_cleanup/local_backup_register_private.md`
- `/private/backup/location/MANIFEST.txt`

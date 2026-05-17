# Nextcloud Golden Baseline Restore

This document defines the frozen Nextcloud baseline used by Axiovance
AWS and local Docker deployments.

## Official baseline

The official v1 archive is stored outside Git:

runtime/ai_decision_studio_functional_baseline/nextcloud_golden_baseline/nextcloud-golden-baseline-v1.tar.gz

Manifest:

runtime/ai_decision_studio_functional_baseline/nextcloud_golden_baseline/nextcloud-golden-baseline-v1.manifest.json

SHA256:

4dd4fb301249fa2ed6e6cc7e223df3beaed2a175b85c352b24ff3ca95636ddb2

## What this baseline contains

- Nextcloud 29 app volume mounted at /var/www/html
- user: danyel
- EvidenceOps corpus under /EvidenceOpsDemo
- WebDAV expected by Product API:

EVIDENCEOPS_REPOSITORY_BACKEND=nextcloud_webdav
EVIDENCEOPS_NEXTCLOUD_BASE_URL=http://nextcloud/remote.php/dav/files/danyel
EVIDENCEOPS_NEXTCLOUD_USERNAME=danyel
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo

EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD must be supplied through the real runtime env
file, such as `.env.aws`, or entered during restore. It must not be committed.

## Redeploy rule

For future redeploys:

1. Upload app bundle.
2. Restore Axiovance data root.
3. Upload nextcloud-golden-baseline-v1.tar.gz from the local baseline folder.
4. Restore the archive into Docker volume ai-decision-studio_nextcloud_app.
5. Configure trusted_domains for localhost, 127.0.0.1 and nextcloud.
6. Configure the real env file to use the same WebDAV user restored in the
   volume.
7. Delete the uploaded tar.gz from the VM after restore.
8. Validate Nextcloud import, EvidenceOps and Overview.

## Do not

- Do not regenerate this from the current local phase95_nextcloud unless intentionally promoting a new v2 baseline.
- Do not commit the tar.gz to Git.
- Do not leave restore archives permanently on the AWS VM.
- Do not expect the app to access `/EvidenceOpsDemo` without a valid WebDAV
  username and app-password.

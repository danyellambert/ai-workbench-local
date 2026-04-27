# Local Backup Register

This file records local safety backups created before repository hardening, seed extraction, multi-user refactoring, Dockerization, or deployment preparation.

Do not commit secrets, .env contents, API keys, or private credentials here.

## Backup 2026-04-27 11:14 America/Sao_Paulo

Purpose:

- Preserve the complete local working tree before production-readiness changes.
- Preserve ignored state that Git branches do not protect.
- Preserve runtime state, artifacts, benchmarks, local data, frontend build context, and source files.
- Preserve Git history separately using a Git bundle.

Backup root:

/Users/danyellambert/Downloads/aula4_SAFE_BACKUP_2026_04_27_111457

Working tree backup:

/Users/danyellambert/Downloads/aula4_SAFE_BACKUP_2026_04_27_111457/Aula 4 - Criacao de Chatbot com IA em Tempo Real

Git bundle:

/Users/danyellambert/Downloads/aula4_SAFE_BACKUP_2026_04_27_111457/repository_all_refs.bundle

Manifest:

/Users/danyellambert/Downloads/aula4_SAFE_BACKUP_2026_04_27_111457/MANIFEST.txt

Source Git HEAD:

1143ddce03df6da7a4d04503d0cf6db99f00710a

Source branch:

main

Important local state preserved:

- .runtime
- .chroma_rag
- .env
- artifacts
- benchmark_runs
- benchmark_pdfs
- data
- frontend
- src

Validation notes:

- Safe backup size: approximately 5.3 GB.
- Git bundle verification: OK.
- .git was intentionally excluded from the working tree backup.
- Git history is preserved in repository_all_refs.bundle.

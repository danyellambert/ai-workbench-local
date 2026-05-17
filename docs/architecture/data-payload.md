# Docker and AWS data payload

The current product is fed by a data payload with four roots:

- baseline
- runtime
- artifacts
- users

Inside the local repository, the versioned deploy payload lives at:

- runtime/ai_decision_studio_functional_baseline/oracle_like_data/baseline
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/runtime
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/artifacts
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/users

In the product container, these are mounted as:

- /app/baseline
- /app/runtime
- /app/artifacts
- /app/users

On AWS, the equivalent host structure is:

- /opt/ai-decision-studio/data/baseline
- /opt/ai-decision-studio/data/runtime
- /opt/ai-decision-studio/data/artifacts
- /opt/ai-decision-studio/data/users

The repository should not treat the entire historical runtime directory as deploy payload. The current deploy payload is specifically oracle_like_data with the four mounted roots above.

What each root means:

- baseline: curated baseline content, public corpus, benchmark/artifact seeds, and read-only reference state.
- runtime: mutable application state, logs, workflow history, eval state, RAG state, and runtime controls.
- artifacts: generated presentation exports, previews, payloads, manifests, and render metadata.
- users: user overlays, session state, and product/user-level persisted state.

Important distinction:

The Docker image build should not copy this payload into the image. The current compose topology mounts the payload at runtime through bind mounts. This keeps image builds smaller and keeps operational data separate from application code.

Files that should stay out of the payload versioning policy:

- local backups;
- .DS_Store;
- tar.gz backup archives;
- unrelated historical runtime snapshots.

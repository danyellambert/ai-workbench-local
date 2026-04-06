# Phase 10 — Engineering Hardening

## Goal

Close the engineering-hardening track with a more reliable baseline for execution, smoke validation, observability, and maintainability.

## What entered this phase

- `Dockerfile` and `.dockerignore` for reproducible execution of the main application
- centralized logging in `src/services/app_logging.py`
- a minimum standard for UI error messages in `src/services/app_errors.py`
- real Streamlit smoke tests using `streamlit.testing.v1`
- extraction of the MCP panel into `src/ui/evidenceops_mcp_panel.py` to reduce coupling in `main.py`
- aggregated measurement of dominant runtime latency bottlenecks (`retrieval`, `generation`, `prompt_build`, `other`)
- CI coverage for smoke tests and focused observability tests

## Engineering decisions

### 1. Real application smoke tests

Instead of validating only static composition, this phase covers both main application entrypoints:

- `main.py` with minimal chat interaction and local fallback without `OPENAI_API_KEY`
- `main.py` with full rendering, operational tabs, and critical controls present

This reduces silent regressions in Streamlit composition, session state, and application assembly.

### 2. Controlled failures in structured execution

The structured execution flow in `main.py` now captures unexpected failures at the top-level submit boundary and converts them into controlled `StructuredResult` outputs via `attempt_controlled_failure`.

As a result:

- the UI no longer fails completely on unexpected errors
- execution remains auditable
- the runtime log still records the attempt
- the observability surface remains coherent

### 3. Standardized logs and messages

Critical points in the application now use centralized logging and more consistent UI-facing error messages.

Direction adopted:

- detailed logs for engineering inspection
- short, consistent messages for the UI
- explicit fallback behavior when retrieval, MCP, or structured execution fails

### 4. Structural clarity

The EvidenceOps MCP panel was extracted out of `main.py` into a dedicated UI module.

Benefits:

- reduced coupling in the main entrypoint
- improved readability of the application shell
- isolation of a full functional slice of the UI
- easier future evolution and testing of the MCP console

### 5. Bottleneck observability

The runtime log now summarizes the relative contribution of latency stages per execution:

- retrieval
- generation
- prompt build
- other

In addition to absolute latency averages, the app can highlight which stage most frequently dominates total execution time.

## Evidence for this phase

- Streamlit smoke tests in `tests/test_streamlit_app_smoke_unittest.py`
- runtime observability in `src/storage/runtime_execution_log.py` and `src/ui/sidebar.py`
- this phase document in `docs/PHASE_10_ENGINEERING_PROFESSIONAL.md`

## Result

Phase 10 establishes a more professional engineering baseline with:

- local and Docker-based execution
- CI with smoke tests and focused checks
- controlled handling of critical failures
- centralized logging
- clearer separation between entrypoints and UI components
- operational metrics useful for performance and maintainability analysis

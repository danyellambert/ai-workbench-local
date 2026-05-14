#!/usr/bin/env bash
set -euo pipefail

# Current Python test gate for Axiovance.
#
# This is intentionally smaller than `python -m unittest discover`.
# It covers the current deterministic/offline-ish Python subset that is
# expected to pass today, while legacy/live/provider-heavy tests remain
# documented in tests/README.md.
#
# Usage:
#   python3 -m pip install -r requirements.txt
#   scripts/run_current_test_gate.sh
#
# To force a Python interpreter:
#   PYTHON=python3.11 scripts/run_current_test_gate.sh

PYTHON_BIN="${PYTHON:-python3}"

echo "== Python =="
"$PYTHON_BIN" --version

echo
echo "== Current Python test gate =="
"$PYTHON_BIN" -m unittest \
  tests.test_app_bootstrap_smoke_unittest \
  tests.test_product_presenters_unittest \
  tests.test_document_context_runtime_unittest \
  tests.test_runtime_execution_log_unittest \
  tests.test_document_agent_unittest \
  tests.test_model_comparison_service_unittest \
  tests.test_pdf_extraction_unittest \
  tests.test_structured_service_unittest \
  tests.test_checklist_and_evidence_eval_unittest \
  tests.test_lab_chat_unittest \
  tests.test_lab_evidenceops_payload \
  tests.test_presentation_export_service_unittest \
  tests.test_presentation_export_unittest

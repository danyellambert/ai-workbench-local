# Phase 5.5 — Framework Evolution with LangChain and LangGraph

## Goal

Show the progression from manual foundations to framework-assisted workflows without discarding the manual baseline.

## What was introduced

- experimental LangChain-based loader paths
- experimental LangChain-based chunking paths
- experimental LangChain + Chroma retrieval paths
- shadow comparison between manual and framework retrieval strategies
- a local history for those comparisons
- an initial LangGraph workflow path for structured task execution
- shadow comparison between direct execution and LangGraph-based retry workflows
- clearer separation between generation providers and embedding providers
- extraction of reranking logic into a dedicated module
- an optional Hugging Face local runtime track for controlled experimentation

## Design principle

The repository kept the manual implementation as the operational baseline while exposing framework-assisted alternatives as:

- selectable
- bounded
- auditable
- reversible

## Why this phase mattered

This phase made the architectural evolution explicit. It showed that the repository can adopt common ecosystem tools where they help, without turning the system into a framework-dependent black box.

## Main supporting artifacts

- `old/docs/PHASE_5_5_LANGCHAIN_EVOLUTION.md`
- `scripts/report_phase55_langchain_shadow_log.py`
- `scripts/report_phase55_langgraph_shadow_log.py`
- `tests/test_langgraph_workflow.py`
- `tests/test_phase55_langgraph_shadow_log.py`

## Closure

Phase 5.5 is complete because the framework evolution path is already implemented, auditable, and documented as an explicit extension of the manual baseline rather than a replacement hidden behind the UI.

## Transition to the next phase

With framework-assisted orchestration available, the next milestone focused on business-oriented tools and agent workflows.

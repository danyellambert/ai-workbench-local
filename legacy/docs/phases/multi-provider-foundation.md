# Phase 3 — Multi-Provider Foundation

## Goal

Prepare the project to work with multiple models and multiple providers without making cloud dependencies mandatory.

## What was implemented

- explicit provider selection in the UI
- model selection per provider
- configurable prompt profiles
- system prompts derived from the selected profile
- message metadata capturing:
  - provider
  - model
  - prompt profile
  - temperature
  - response latency
- conversation rendering with those metadata signals visible
- a provider registry foundation

## Providers in scope for this phase

### Default active path

- `ollama`

### Optional configured path

- `openai`

## Why this phase mattered

This phase reduced coupling and prepared the project for:

- local model comparison
- future local-versus-cloud comparisons
- provider-aware logging
- later evaluation by scenario and runtime

## Source notes retained from the original phase record

The original Portuguese phase notes were preserved in:

- `old/docs/PHASE_3_NOTES.md`

## Closure

Phase 3 is complete because the repository no longer assumes a single provider path for the core application flow.

## Transition to the next phase

With multi-provider handling in place, the next logical step was document-grounded RAG.

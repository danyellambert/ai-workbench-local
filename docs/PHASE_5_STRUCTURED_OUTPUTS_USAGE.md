# Phase 5 Structured Outputs Usage Guide

## What is already working

The project now has a usable Phase 5 structured-output flow with:

- task selection in the main app UI
- validated payloads via Pydantic
- JSON, friendly view, and checklist view render modes
- optional document grounding via the current RAG document selection
- basic quality heuristics to warn when the output looks placeholder-like or poorly grounded

## Recommended usage by task

### 1. `summary`
Best for:
- summarizing uploaded documents
- generating an executive view of document content
- comparing pasted text with document-grounded context

Recommended input:
- enable **Use current document context (RAG)** when working from indexed files
- optionally add a short user prompt such as:
  - `Summarize the main points for a project review`
  - `Give me the executive summary of this document`

### 2. `extraction`
Best for:
- extracting entities, categories, relationships, and named fields from a document or pasted text

Recommended input:
- use pasted text for short factual extraction tasks
- use RAG when the source is an indexed document and you want evidence-backed extraction

### 3. `checklist`
Best for:
- converting requirements, procedures, or operational notes into an actionable checklist

Recommended input:
- concrete instructions or process documents
- RAG-enabled execution when the source material lives in uploaded files

### 4. `cv_analysis`
Best for:
- structuring resume content
- extracting personal/contact info, sections, skills, and high-level strengths/improvement areas

Recommended input:
- prefer **Use current document context (RAG)** with the resume selected in the current document filter
- if you do not use RAG, paste the resume text directly into the input box

Important note:
- this mode is grounded better than the first stub version, but it is still not a hiring decision engine
- it should be treated as a structured analysis helper, not an objective evaluation system

## Good operating patterns

### When to rely on pasted text
Use pasted text when:
- the source is short
- you want fast iteration
- you do not need the indexed-document context

### When to rely on RAG
Use RAG when:
- the source lives in uploaded/indexed documents
- you want the task to stay grounded in the currently selected files
- the document is too long to paste comfortably

### Best practice for CV analysis
For the best CV results:
1. upload/index the CV
2. filter/select the CV in the document panel
3. choose `cv_analysis`
4. enable **Use current document context (RAG)**
5. optionally add a short note in the input field, such as `analyze this resume for structure and skills`

## Current limitations

- the task layer is already useful, but prompt tuning can still be improved further
- `code_analysis` is not implemented yet
- real benchmark/eval coverage for structured outputs is still pending
- results can still vary depending on provider/model quality

## What to look for in the UI

A healthy structured-output result should show:
- `Validated`
- `with RAG` when document context was used
- no low-quality/placeholder warning banner

If you see a low-quality warning, try:
- enabling document context
- providing richer source text
- avoiding empty input with no supporting document context

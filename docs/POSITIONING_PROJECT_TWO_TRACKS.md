# Project Positioning — Two Official Tracks

## Purpose

This document defines the official reading of the repository so it does not appear as either:

- a generic lab with no product center
- or two unrelated projects living in the same codebase

The repository is best understood through **two complementary tracks**.

## Official thesis

AI Workbench Local is an applied AI platform with two linked layers:

1. **Business Workflows**
   - document-grounded workflows that help turn source material into findings, recommendations, actions, and reusable artifacts

2. **AI Engineering Lab**
   - the engineering layer that benchmarks, evaluates, instruments, and evolves the systems behind those workflows

These are not competing products.

The intended reading is:

- the **workflow layer** solves a real document problem
- the **engineering layer** keeps that workflow measurable, auditable, and evolvable

## Track 1 — Business Workflows

### Core problem

Organizations often need to transform documents into:

- grounded answers
- comparative analysis
- structured findings
- operational action plans
- executive-ready artifacts for human review

### Official product framing

The main product framing is:

> **Document-grounded decision workflows**

### Representative workflows

- **Document Review**
- **Policy / Contract Comparison**
- **Action Plan / Evidence Review**
- **Candidate Review**

### Transversal capability

Executive deck generation is treated as a transversal capability of those workflows rather than as a competing standalone product surface.

## Track 2 — AI Engineering Lab

### Core questions

This layer exists to answer engineering questions such as:

- which model or runtime behaves best for a given workload?
- when is retrieval sufficient and when is another strategy needed?
- how do we measure quality repeatedly?
- how do we audit latency, cost, fallbacks, and workflow decisions?

### Official lab framing

The lab layer is the place for:

- benchmark execution
- evaluation and diagnosis
- observability and runtime analysis
- routing and guardrail analysis
- controlled architecture experimentation

## Practical boundary

### Product-facing emphasis

The workflow layer should emphasize:

- document understanding
- findings and recommendations
- structured action outputs
- reusable executive artifacts

### Engineering-facing emphasis

The lab layer should emphasize:

- measurement
- auditability
- reproducibility
- controlled change management

## Why this structure matters

Without this distinction, the repository can look broader than it is. With it, the project reads as:

- a document-centered applied AI system
- backed by a serious engineering layer for reliability and evolution

That separation improves readability for collaborators, reviewers, and future maintainers.

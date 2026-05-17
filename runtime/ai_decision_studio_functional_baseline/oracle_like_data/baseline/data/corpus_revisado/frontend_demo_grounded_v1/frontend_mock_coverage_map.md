# Frontend mock coverage map

## Base decision
- Official base audited first: `data/corpus_revisado/option_b_synthetic_premium`
- Derived corpus created: `data/corpus_revisado/frontend_demo_grounded_v1`
- Public reference retained as complementary only: `data/corpus_revisado/option_a_public_corpus_v2`

## Workflow coverage

### 1. Document Review
- `contracts/Master Service Agreement v4.2.pdf`
  - Section 7.3 → unlimited liability
  - Section 7.5 → indemnification scope
  - Section 7.8 → 12-month claim window
  - Section 8.2 → 90-day auto-renewal notice
- `contracts/Data Processing Addendum 2024.pdf`
  - Clauses 5.2 / 5.4 → no explicit residency + SCC appendix deferred
- `contracts/Cloud Infrastructure SLA.pdf`
  - metric table → 99.5% uptime
  - clause 4.2 → capped liability under SLA
- `policies/Information Security Policy v3.1.pdf`
  - REQ-IR-07 → “reasonable efforts” incident timing

### 2. Policy / Contract Comparison
- MSA draft vs approved baseline vs legal redline summary ground liability, notice, and IP diffs
- DPA + GDPR checklist ground data residency / SCC diffs
- SLA grounds uptime / service-credit diffs
- Policy v3.1 vs v3.2 grounds internal policy change detection

### 3. Action Plan / Evidence Review
- Audit checklist → findings source
- NCR → corrective actions
- Evidence log → provenance register
- Approval email → attached evidence artifact
- Governance minutes → owner / due date / status chain
- Vendor risk assessment export → blocked SOC2 row and open risk register
- Closure note → closure readiness

### 4. Candidate Review
- CV + role brief + scorecard + interview memo provide strengths, gaps, seniority signals, and recommendation
- Exact mock employer names were not reproduced; capability signals were preserved using fictional employers for safety

### 5. Chat / RAG
Grounded answers can be supported from:
- MSA v4.2
- Cloud Infrastructure SLA
- Data Processing Addendum 2024
- Information Security Policy v3.1 / v3.2
- Data Retention Policy
- Internal Audit Checklist

### 6. Workflow Inspector / structured extraction
Strong structured extraction candidates:
- contracting party
- effective date
- annual value
- term duration
- governing law
- liability cap / uncapped language
- notice period
- requirement IDs
- approval names and dates

### 7. Document Library realism
Format diversity included:
- contract PDFs
- policy PDFs
- audit / NCR / evidence PDFs
- email export PDF
- spreadsheet export PDF
- board memo PDF
- handbook PDF
- technical architecture brief with OCR-hard image pages 12–15

## UI-only / operational-only items
These remain frontend or system-state fields and are not expected to come directly from documents:
- indexing status, chunk counts, character counts, loader strategy, latency, workflow run duration, system stats, artifact generation timestamps

## Remaining partials
- Candidate pack is substantively grounded, but employer / institution names were fictionalized to avoid inventing a résumé at real organizations.
- Some comparison surfaces collapse multiple supporting documents into a single UI comparison. The corpus supports those diffs as a document bundle rather than a single two-file pair in every case.

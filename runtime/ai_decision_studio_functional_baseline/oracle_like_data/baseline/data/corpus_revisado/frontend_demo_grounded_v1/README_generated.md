# frontend_demo_grounded_v1

## Objective
This derived corpus grounds the frontend demo in document evidence instead of primarily static mocks.
It preserves the best parts of `option_b_synthetic_premium` while aligning dates, filenames, clause patterns,
workflow outputs, and supporting artifacts to the March 2024 frontend scenario.

## Core storyline
- Customer: **Meridian Holdings Ltd.**
- Vendor: **Northwind Cloud Systems LLC**
- Review window: **March 2024**
- Main commercial themes: unlimited liability, missing SCCs / data residency, 99.5% SLA, 90-day auto-renewal, vague incident notice
- Main operational themes: missing access-review approval evidence, governance escalation, action planning, temporary uptime waiver, closure readiness
- Hiring theme: **Sarah Chen** reviewed for **Senior ML Engineer** role with a grounded scorecard and panel memo

## Relationship to the existing corpus
### Reused as foundation
The official base remains `data/corpus_revisado/option_b_synthetic_premium`.
This derived corpus reuses that base as the narrative and structural starting point for:
- contract / policy / audit / evidence storylines
- document taxonomy and metadata conventions
- clause-based review and remediation chains

### Derived / rewritten from Option B
These documents are direct derivatives of Option B counterparts, rewritten for the frontend scenario:
- `contracts/Master Service Agreement v4.2.pdf`
- `contracts/MSA Negotiation Baseline - Approved Position.pdf`
- `contracts/Cloud Infrastructure SLA.pdf`
- `contracts/Data Processing Addendum 2024.pdf`
- `policies/Information Security Policy v3.1.pdf`
- `policies/Information Security Policy v3.2.pdf`
- `policies/Data Retention Policy.pdf`
- `policies/Third-Party Supplier Code of Conduct.pdf`
- `audit/Internal Audit Checklist - Vendor Controls.pdf`
- `audit/Nonconformance Report - Vendor Access Review.pdf`
- `audit/Access Review Evidence Log.pdf`
- `audit/Governance Committee Minutes and Action Items.pdf`

### Created from scratch
These documents were created specifically to close frontend and realism gaps:
- `legal/Legal Redline Summary - MSA v4.2.pdf`
- `governance/GDPR Compliance Checklist.pdf`
- `risk/Vendor Risk Assessment Template.pdf`
- `evidence/Privileged Account Approval Email.pdf`
- `risk/Temporary Risk Acceptance Request - SLA Uptime.pdf`
- `privacy/Subprocessor Change Notice.pdf`
- `audit/Remediation Closure Note - Vendor Access Review.pdf`
- `operations/Employee Handbook 2024.pdf`
- `technical/Technical Architecture Brief.pdf`
- `governance/Q1 2024 Board Memo.pdf`
- all documents under `hiring/`

## Frontend coverage highlights
- **Document Review**: grounded by MSA v4.2, DPA 2024, Cloud Infrastructure SLA, and Information Security Policy v3.1
- **Comparison**: grounded by MSA v4.2, approved MSA baseline, legal redline summary, DPA 2024, SLA, and policy v3.1 → v3.2
- **Action Plan / Evidence Review**: grounded by audit checklist, NCR, evidence log, approval email, committee minutes, risk register, and closure note
- **Candidate Review**: grounded by CV, role brief, scorecard, and interview memo
- **Chat / RAG**: clause, policy, SLA, retention, and audit questions can be answered with document references
- **Workflow Inspector**: structured extraction is supported by explicit document control blocks, clause IDs, requirement IDs, dates, owners, and approval records
- **Document Library realism**: includes contracts, policies, audit docs, a board memo, handbook, spreadsheet-export PDF, email PDF, and an OCR-hard technical brief

## Special format coverage
- Email-style PDF: `evidence/Privileged Account Approval Email.pdf`
- Spreadsheet-export PDF: `risk/Vendor Risk Assessment Template.pdf`
- OCR-hard / scan-heavy PDF: `technical/Technical Architecture Brief.pdf` (pages 12–15 are image-only appendices)

## Metadata files
- `corpus_manifest.json`
- `corpus_manifest.csv`
- `frontend_mock_coverage_map.md`
- `frontend_mock_coverage_map.json`
- `corpus_gap_report.md`

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, CheckCircle2, Compass, ExternalLink, Sparkles, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type TourAction =
  | 'open-nextcloud-import'
  | 'focus-nextcloud-root'
  | 'focus-nextcloud-synthetic'
  | 'select-nextcloud-starter-set'
  | 'open-action-plan-board'
  | 'open-candidate-internals';

type TourPlacement = 'above' | 'below' | 'left' | 'right' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
type TourScrollBlock = 'start' | 'center' | 'end' | 'nearest';

type TourStep = {
  id: string;
  path: string;
  selector: string;
  fallbackSelector?: string;
  eyebrow: string;
  title: string;
  body: string;
  bullets?: string[];
  tip?: string;
  actions?: TourAction[];
  cta?: {
    label: string;
    action: TourAction;
  };
  link?: {
    label: string;
    href: string;
  };
  placement?: TourPlacement;
  scrollBlock?: TourScrollBlock;
  panelWidth?: number;
  forcePlacement?: boolean;
  compactPanel?: boolean;
  spotlightOffset?: { x?: number; y?: number; width?: number; height?: number };
};

type ActiveTourKind = 'document-library' | 'workflow' | 'document-review' | 'policy-comparison' | 'action-plan' | 'candidate-review' | 'deck-center' | 'run-history' | 'runtime-controls' | 'preferences' | 'lab-overview' | 'lab-runtime' | 'lab-document-experiments' | 'lab-workflow-inspector' | 'lab-benchmarks' | 'lab-evals' | 'lab-artifacts' | 'lab-evidenceops';

type TourRect = { top: number; left: number; width: number; height: number };
type PanelCandidate = { placement: TourPlacement; left: number; top: number; maxHeight?: number; visibleHeight?: number; collision?: number; overflow?: number; fits?: boolean };

const DANYEL_LINKEDIN_URL = 'https://www.linkedin.com/in/danyel-/';
const TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-document-library-complete';
const WORKFLOW_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-workflow-complete';
const DOCUMENT_REVIEW_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-document-review-complete';
const POLICY_COMPARISON_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-policy-comparison-complete';
const ACTION_PLAN_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-action-plan-complete';
const CANDIDATE_REVIEW_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-candidate-review-complete';
const DECK_CENTER_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-deck-center-complete';
const RUN_HISTORY_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-run-history-complete';
const RUNTIME_CONTROLS_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-runtime-controls-complete';
const PREFERENCES_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-preferences-complete';
const LAB_OVERVIEW_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-overview-complete';
const LAB_RUNTIME_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-runtime-complete';
const LAB_DOCUMENT_EXPERIMENTS_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-document-experiments-complete';
const LAB_WORKFLOW_INSPECTOR_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-workflow-inspector-complete';
const LAB_BENCHMARKS_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-benchmarks-complete';
const LAB_EVALS_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-evals-complete';
const LAB_ARTIFACTS_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-artifacts-complete';
const LAB_EVIDENCEOPS_TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-lab-evidenceops-complete';

const DOCUMENT_LIBRARY_TOUR_STEPS: TourStep[] = [
  {
    id: 'command-center-hero',
    path: '/app',
    selector: '[data-tour="command-center-hero"]',
    fallbackSelector: '[data-tour="command-center-hero-content"]',
    eyebrow: 'Step 1 - Command Center',
    title: 'Start with the workbench overview.',
    body: 'Use this first screen to understand the product promise: bring documents in, run grounded workflows, and turn the results into decisions and artifacts.',
    tip: 'Start here when you want a quick read on what the workspace is ready to do before opening any workflow.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'command-center-metrics',
    path: '/app',
    selector: '[data-tour="command-center-metrics"]',
    eyebrow: 'Step 2 - Readiness',
    title: 'Check what is already prepared.',
    body: 'These cards show the current state of the workspace: indexed documents, available chunks, completed runs, and generated artifacts. Use them to confirm that the demo has enough evidence to run.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'command-center-workflows',
    path: '/app',
    selector: '[data-tour="command-center-workflows"]',
    eyebrow: 'Step 3 - Workflow map',
    title: 'Choose the job before choosing files.',
    body: 'Each workflow answers a different kind of question. Document Review inspects one file deeply, Policy Comparison compares related files, Action Plan turns findings into work, and Candidate Review focuses on hiring evidence.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'command-center-activity',
    path: '/app',
    selector: '[data-tour="command-center-activity"]',
    eyebrow: 'Step 4 - Activity and shortcuts',
    title: 'Use recent activity and shortcuts when the corpus is ready.',
    body: 'Recent Runs shows what was executed most recently. Quick Launch is useful after the right documents are indexed and you want to jump straight into a workflow.',
    tip: 'For this walkthrough, take the cleaner setup path first: open the Document Library and bring in curated evidence.',
    placement: 'above',
    scrollBlock: 'center',
    panelWidth: 620,
    forcePlacement: true,
    compactPanel: true,
  },
  {
    id: 'command-center-lab-artifacts',
    path: '/app',
    selector: '[data-tour="command-center-lab-artifacts"]',
    eyebrow: 'Step 5 - Lab and outputs',
    title: 'Use the lower cards for deeper inspection and generated outputs.',
    body: 'The AI Engineering Lab leads to observability, benchmarks, evaluations, and MCP/evidence surfaces. Recent Artifacts shows the decks and outputs generated from workflow runs.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'nav-documents',
    path: '/app',
    selector: '[data-tour="nav-documents"]',
    eyebrow: 'Step 6 - Navigation',
    title: 'Next, open the Document Library.',
    body: 'Every grounded workflow starts from indexed documents. The sidebar keeps the main product areas one click away as you move through the workspace.',
    placement: 'right',
    scrollBlock: 'nearest',
  },
  {
    id: 'documents-actions',
    path: '/app/documents',
    selector: '[data-tour="documents-page-actions"]',
    eyebrow: 'Step 7 - Ingestion choices',
    title: 'For the public demo, use the curated import path.',
    body: 'Choose Import from Nextcloud to browse the prepared corpus and add selected PDFs to this workspace. Upload Documents is reserved for guided or private demos when a visitor wants to test their own files.',
    link: {
      label: 'Connect with Danyel on LinkedIn',
      href: DANYEL_LINKEDIN_URL,
    },
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { y: -7 },
  },
  {
    id: 'documents-pipeline',
    path: '/app/documents',
    selector: '[data-tour="documents-pipeline"]',
    eyebrow: 'Step 8 - Pipeline clarity',
    title: 'Watch the indexing steps as files arrive.',
    body: 'As files are imported, this pipeline shows extraction, chunking, embeddings, and index sync. You can see what the app is preparing instead of waiting on hidden background work.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'documents-table',
    path: '/app/documents',
    selector: '[data-tour="documents-indexed-sample"]',
    fallbackSelector: '[data-tour="documents-indexed-table"]',
    eyebrow: 'Step 9 - Indexed library',
    title: 'This is the evidence the workflows will use.',
    body: 'After indexing, documents appear here with status, chunks, characters, loader, and actions. Use this table to confirm that the corpus is ready before launching a workflow.',
    placement: 'below',
    scrollBlock: 'start',
  },
  {
    id: 'nextcloud-folders',
    path: '/app/documents',
    selector: '[data-tour="nextcloud-folder-list"]',
    eyebrow: 'Step 10 - Curated corpora',
    title: 'Open the prepared corpus and choose the right folder.',
    body: 'Nextcloud keeps two main corpus areas: Demo Synthetic Corpus for polished walkthrough files, and Public Reference Corpus for public documents that feel closer to real-world evidence.',
    bullets: [
      'Demo Synthetic Corpus: best for a safe, polished public walkthrough.',
      'Public Reference Corpus: best when you want realistic policy, contract, audit, or comparison material.',
    ],
    tip: 'For the first run, start with Demo Synthetic Corpus. It is the smoothest way to see the import flow, selected files, and product workflows working end to end.',
    actions: ['open-nextcloud-import', 'focus-nextcloud-root'],
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'nextcloud-workflow-choice',
    path: '/app/documents',
    selector: '[data-tour="nextcloud-file-selection"]',
    eyebrow: 'Step 11 - Starter files',
    title: 'Select a starter set for the workflow tour.',
    body: 'For a quick end-to-end demo, import this focused set from Demo Synthetic Corpus:',
    bullets: [
      'Document Review: Master Service Agreement v4.2.pdf.',
      'Policy Comparison: Information Security Policy v3.1.pdf + Information Security Policy v3.2.pdf.',
      'Action Plan: Governance Committee Minutes and Action Items.pdf + Internal Audit Checklist - Vendor Controls.pdf + Nonconformance Report - Vendor Access Review.pdf + Remediation Closure Note - Vendor Access Review.pdf.',
      'Candidate Review: Sarah Chen - Senior ML Engineer CV.pdf + Senior ML Engineer Role Brief.pdf.',
    ],
    tip: 'This set gives the next workflow tour enough evidence without making you hunt through every folder.',
    actions: ['open-nextcloud-import', 'focus-nextcloud-synthetic'],
    cta: {
      label: 'Select recommended starter set',
      action: 'select-nextcloud-starter-set',
    },
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'nextcloud-selection',
    path: '/app/documents',
    selector: '[data-tour="nextcloud-selection-controls"]',
    eyebrow: 'Step 12 - Multi-select',
    title: 'Select several PDFs in one pass.',
    body: 'You can open folders, check individual files, or use Select all shown PDFs when the current folder already contains exactly the documents you want.',
    tip: 'Keep the selection focused. Import only the documents you plan to use in the upcoming workflow demo.',
    actions: ['open-nextcloud-import', 'focus-nextcloud-synthetic'],
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'nextcloud-import-action',
    path: '/app/documents',
    selector: '[data-tour="nextcloud-import-action"]',
    eyebrow: 'Step 13 - Import batch',
    title: 'Preview individual files if needed, then import the selected batch.',
    body: 'Use the small View button on any file card when you want a quick preview. When the selected batch looks right, Import sends every selected PDF into the Document Library as one clean indexing job.',
    tip: 'Finish here when you want to inspect the library. A small Continue tour cue will pulse over Workflows so you can move into the next phase when you are ready.',
    actions: ['open-nextcloud-import', 'focus-nextcloud-synthetic'],
    placement: 'above',
    scrollBlock: 'center',
  },
];


const WORKFLOW_TOUR_STEPS: TourStep[] = [
  {
    id: 'workflow-catalog-header',
    path: '/app/workflows',
    selector: '[data-tour="workflow-catalog-header"]',
    eyebrow: 'Step 1 - Workflow catalog',
    title: 'Start by choosing the decision workflow.',
    body: 'This page is the live catalog of jobs the workbench can run. It connects the workflow contract, indexed document corpus, and persisted run history before you open a specific workflow.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -10, width: 20, height: 20 },
  },
  {
    id: 'workflow-catalog-surface',
    path: '/app/workflows',
    selector: '[data-tour="workflow-catalog-surface"]',
    eyebrow: 'Step 2 - Live readiness',
    title: 'Confirm the run surface is ready.',
    body: 'This strip summarizes how many workflow definitions are loaded, how many grounded documents are available, and how much run history the product can use for context.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'workflow-document-review-card',
    path: '/app/workflows',
    selector: '[data-tour="workflow-card-document_review"]',
    eyebrow: 'Step 3 - Document Review',
    title: 'Document Review is the simplest first workflow.',
    body: 'Use this card when the user wants to inspect one indexed document deeply, summarize key findings, surface risks, and generate review-ready artifacts.',
    tip: 'Read the inputs, outputs, badges, and live signals before opening the workflow. They explain whether the current corpus is ready to run.',
    placement: 'below',
    scrollBlock: 'center',
    forcePlacement: true,
  },
  {
    id: 'workflow-policy-comparison-card',
    path: '/app/workflows',
    selector: '[data-tour="workflow-card-policy_contract_comparison"]',
    eyebrow: 'Step 4 - Policy comparison',
    title: 'Policy / Contract Comparison needs a document pair.',
    body: 'This card is for comparing related versions or related agreements. It keeps the two-document requirement clear before the user moves into the side-by-side comparison workspace.',
    placement: 'below',
    scrollBlock: 'center',
    forcePlacement: true,
  },
  {
    id: 'workflow-action-plan-card',
    path: '/app/workflows',
    selector: '[data-tour="workflow-card-action_plan_evidence_review"]',
    eyebrow: 'Step 5 - Action plan',
    title: 'Action Plan / Evidence Review turns findings into work.',
    body: 'Use this workflow when several grounded documents need to become owners, tasks, blockers, timelines, evidence gaps, and downstream handoff outputs.',
    placement: 'above',
    scrollBlock: 'center',
    forcePlacement: true,
  },
  {
    id: 'workflow-candidate-review-card',
    path: '/app/workflows',
    selector: '[data-tour="workflow-card-candidate_review"]',
    eyebrow: 'Step 6 - Candidate Review',
    title: 'Candidate Review focuses the same grounded pattern on hiring evidence.',
    body: 'This card shows the CV-oriented workflow. It can evaluate a candidate document and optionally use an indexed role brief to keep the assessment role-aware.',
    tip: 'Finish this overview here. The Continue tour cue will restart cleanly inside Document Review so the product walkthrough moves from the catalog into the first workflow.',
    placement: 'above',
    scrollBlock: 'center',
    forcePlacement: true,
  },
];

const DOCUMENT_REVIEW_TOUR_STEPS: TourStep[] = [
  {
    id: 'document-review-header',
    path: '/app/workflows/document-review',
    selector: '[data-tour="document-review-header"]',
    eyebrow: 'Step 1 - Review workspace',
    title: 'This is the dedicated Document Review surface.',
    body: 'The header keeps the workflow goal visible and exposes the two main actions: run the grounded review and generate a deck after results are available.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'document-review-progress',
    path: '/app/workflows/document-review',
    selector: '[data-tour="document-review-progress"]',
    eyebrow: 'Step 2 - Workflow progress',
    title: 'Follow the run from selection to export.',
    body: 'The progress rail makes the live state legible: Select, Ground, Analyze, Review, and Export. It shows what is already complete and what still needs to run.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'document-review-decision',
    path: '/app/workflows/document-review',
    selector: '[data-tour="document-review-decision"]',
    eyebrow: 'Step 3 - Decision state',
    title: 'The decision card summarizes the current outcome.',
    body: 'Before running, it explains what the user needs to do. After running, it becomes the executive summary with status, severity counts, next owner, and due date.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'document-review-selection',
    path: '/app/workflows/document-review',
    selector: '[data-tour="document-review-selection"]',
    eyebrow: 'Step 4 - Grounded selection',
    title: 'Choose the source document and inspect grounding.',
    body: 'This left panel picks the indexed document and exposes the grounding preview. It keeps the workflow anchored to real evidence instead of free-form prompts.',
    tip: 'For the smoothest demo, use Master Service Agreement v4.2.pdf. If it has not been indexed yet, leave the selector empty and choose another indexed document from the dropdown.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'document-review-output-tabs',
    path: '/app/workflows/document-review',
    selector: '[data-tour="document-review-output-tabs"]',
    fallbackSelector: '[data-tour="document-review-output-panel"]',
    eyebrow: 'Step 5 - Evidence panels',
    title: 'Review findings, evidence, and generated artifacts here.',
    body: 'The right side organizes the workflow result. Findings are for decisions, Evidence is for traceability, and Artifacts collects generated outputs like decks.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'document-review-supporting-cards',
    path: '/app/workflows/document-review',
    selector: '[data-tour="document-review-supporting-cards"]',
    eyebrow: 'Step 6 - Business interpretation',
    title: 'Use the lower cards to understand what matters.',
    body: 'Top Blockers and Business Impact turn raw findings into operational language, so the user can see what needs attention before signing or publishing.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'document-review-publish',
    path: '/app/workflows/document-review',
    selector: '[data-tour="document-review-publish"]',
    eyebrow: 'Step 7 - Handoff',
    title: 'Publish outputs only after the review is ready.',
    body: 'The publishing area stays downstream from the evidence review. Once findings and artifacts exist, the user can preview Trello cards or a Notion handoff before publishing.',
    placement: 'above',
    scrollBlock: 'center',
  },
];


const POLICY_COMPARISON_TOUR_STEPS: TourStep[] = [
  {
    id: 'policy-comparison-header',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-header"]',
    eyebrow: 'Step 1 - Policy comparison',
    title: 'Start with the comparison workspace.',
    body: 'This workflow compares two related documents side by side and turns the deltas into grounded business guidance.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'policy-comparison-progress',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-progress"]',
    eyebrow: 'Step 2 - Comparison progress',
    title: 'Track the comparison from selection to export.',
    body: 'The progress rail shows when the two documents are selected, grounded, analyzed, reviewed, and ready for export.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-selection',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-selection"]',
    eyebrow: 'Step 3 - Document pair',
    title: 'Choose the two documents that should be compared.',
    body: 'Policy Comparison needs two different indexed documents. The selectors keep both sides explicit instead of letting the workflow guess the pair.',
    tip: 'Use Information Security Policy v3.1.pdf and Information Security Policy v3.2.pdf for the comparison demo.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-grounding',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-grounding"]',
    eyebrow: 'Step 4 - Grounding preview',
    title: 'Keep the evidence preview available but calm.',
    body: 'The grounding preview stays collapsed by default, then opens when someone wants to inspect the retrieved context behind the comparison.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-summary',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-summary"]',
    eyebrow: 'Step 5 - Executive summary',
    title: 'Use the summary to understand the decision impact.',
    body: 'After the workflow runs, this area summarizes breaking, significant, and minor differences with a business-readable narrative.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-priorities',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-priorities"]',
    eyebrow: 'Step 6 - Approval risks',
    title: 'Separate must-fix blockers from negotiation priorities.',
    body: 'These cards translate document differences into what must be fixed before approval and what can be negotiated.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-diffs',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-diffs"]',
    eyebrow: 'Step 7 - Evidence deltas',
    title: 'Review the clause-level differences.',
    body: 'The diff list is where the comparison becomes auditable: each material difference can carry impact, category, source text, and business interpretation.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-recommendation',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-recommendation"]',
    eyebrow: 'Step 8 - Recommendation',
    title: 'End with a decision-ready recommendation.',
    body: 'The recommendation turns the comparison into a suggested path forward and a clear handoff note.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-watchouts-artifacts',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-watchouts-artifacts"]',
    fallbackSelector: '[data-tour="policy-comparison-artifacts"]',
    eyebrow: 'Step 9 - Watchouts and artifacts',
    title: 'Review watchouts and generated artifacts together.',
    body: 'Watchouts call out the caveats that still need human attention, while Generated Artifacts shows the deck and handoff files produced from the comparison.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'policy-comparison-publish',
    path: '/app/workflows/comparison',
    selector: '[data-tour="policy-comparison-publish"]',
    eyebrow: 'Step 10 - Publishing',
    title: 'Publish only after the comparison is reviewed.',
    body: 'The publishing surface is downstream from the summary, deltas, and artifacts so external handoff happens after the evidence is checked.',
    placement: 'above',
    scrollBlock: 'center',
  },
];


const ACTION_PLAN_TOUR_STEPS: TourStep[] = [
  {
    id: 'action-plan-header',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-header"]',
    eyebrow: 'Step 1 - Action plan',
    title: 'Start with the action planning workspace.',
    body: 'This workflow turns grounded findings into execution work: selected evidence, owners, priorities, due dates, blockers, and publish-ready handoff outputs.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'action-plan-progress',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-progress"]',
    eyebrow: 'Step 2 - Run progress',
    title: 'Track the action plan from selection to export.',
    body: 'The progress rail keeps the live workflow state readable: selecting source evidence, grounding context, analyzing actions, reviewing outputs, and exporting the handoff.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'action-plan-selection',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-selection"]',
    eyebrow: 'Step 3 - Grounded evidence set',
    title: 'Choose the documents that should become work.',
    body: 'Action Plan can use several indexed documents at once. The compact selection card keeps the evidence set explicit before extracting owners, tasks, risks, and next steps.',
    tip: 'Use: Governance Committee Minutes and Action Items.pdf; Internal Audit Checklist - Vendor Controls.pdf; Nonconformance Report - Vendor Access Review.pdf; Remediation Closure Note - Vendor Access Review.pdf. Max: four docs.',
    placement: 'below',
    scrollBlock: 'start',
    panelWidth: 520,
    compactPanel: true,
    forcePlacement: true,
    spotlightOffset: { y: 8, height: -30 },
  },
  {
    id: 'action-plan-grounding',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-grounding"]',
    eyebrow: 'Step 4 - Grounding preview',
    title: 'Keep the preview available without overwhelming the page.',
    body: 'The grounding preview stays collapsed until someone wants to inspect context coverage, selected source blocks, and evidence caveats behind the action plan.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'action-plan-status-strip',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-status-strip"]',
    eyebrow: 'Step 5 - Execution status',
    title: 'Use the status strip to read operational load.',
    body: 'These counters summarize open, in-progress, blocked, and completed items once the workflow produces a normalized action plan.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'action-plan-work-views',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-work-views"]',
    eyebrow: 'Step 6 - Work views',
    title: 'Switch between board, table, timeline, and evidence gaps.',
    body: 'The tabs let different users inspect the same grounded output in the shape they need: kanban-style execution, structured table, timeline, or evidence sufficiency.',
    placement: 'below',
    scrollBlock: 'center',
    forcePlacement: true,
    spotlightOffset: { x: 10, y: 10, width: -20, height: -20 },
  },
  {
    id: 'action-plan-board',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-board"]',
    fallbackSelector: '[data-tour="action-plan-work-views"]',
    actions: ['open-action-plan-board'],
    eyebrow: 'Step 7 - Action board',
    title: 'Review the generated work before publishing.',
    body: 'The board area fills after the run. It is the place to check tasks, owners, rationale, deadlines, and status before sending the plan downstream.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'action-plan-run-summary',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-run-summary"]',
    eyebrow: 'Step 8 - Summary and artifacts',
    title: 'Use the run summary and generated artifacts for handoff.',
    body: 'The lower cards turn the action plan into a concise run summary, highlights, watchouts, and generated files that can be reviewed before publishing.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'action-plan-publish',
    path: '/app/workflows/action-plan',
    selector: '[data-tour="action-plan-publish"]',
    eyebrow: 'Step 9 - Publishing',
    title: 'Publish only after the action plan is reviewed.',
    body: 'The publishing surface sits last so Trello cards or Notion handoffs are created after the evidence, board, gaps, and artifacts are checked.',
    placement: 'above',
    scrollBlock: 'center',
  },
];


const CANDIDATE_REVIEW_TOUR_STEPS: TourStep[] = [
  {
    id: 'candidate-review-header',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-header"]',
    eyebrow: 'Step 1 - Candidate review',
    title: 'Start with the hiring review workspace.',
    body: 'Candidate Review evaluates one CV-like document against grounded evidence, then optionally uses an indexed role brief to make the assessment role-aware.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'candidate-review-progress',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-progress"]',
    eyebrow: 'Step 2 - Run progress',
    title: 'Track the review from selection to export.',
    body: 'The progress rail keeps the run state visible while the workflow selects the candidate document, grounds context, analyzes the CV, reviews outputs, and exports handoff assets.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-selection',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-selection"]',
    eyebrow: 'Step 3 - Candidate and role evidence',
    title: 'Choose the CV and the optional role brief.',
    body: 'The left document is the primary candidate evidence. The role brief makes the review fit-aware without changing the backend workflow contract.',
    tip: 'Use Sarah Chen - Senior ML Engineer CV.pdf with Senior ML Engineer Role Brief.pdf. That pair gives the workflow both candidate evidence and role-specific evaluation criteria.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-internals',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-analysis-internals"]',
    eyebrow: 'Step 4 - Analysis internals',
    title: 'Keep grounding details available but collapsed.',
    body: 'This section exposes the candidate grounding preview and generated role-aware prompt only when someone needs retrieval or debugging context.',
    actions: ['open-candidate-internals'],
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-profile',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-profile"]',
    eyebrow: 'Step 5 - Candidate profile',
    title: 'Use the profile card as the live hiring snapshot.',
    body: 'Before a run, it explains what will be populated. After a run, it becomes the concise candidate profile with confidence, status, and run metadata.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-left-insights',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-left-insights"]',
    eyebrow: 'Step 6 - Role context and risks',
    title: 'Separate role context from decision risks.',
    body: 'These supporting cards keep the role requirements, watchouts, and grounded signals visible without mixing them into the main profile summary.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-interview-focus',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-interview-focus"]',
    eyebrow: 'Step 7 - Interview focus',
    title: 'Turn the review into interview next steps.',
    body: 'The interview focus area converts grounded observations into practical prompts for the next human review or interview stage.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-experience',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-experience"]',
    eyebrow: 'Step 8 - Experience evidence',
    title: 'Review structured experience highlights.',
    body: 'Experience rows make the CV evidence easier to scan: role, company, time period, and impact are separated into a grounded summary.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-evaluation-grid',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-evaluation-grid"]',
    eyebrow: 'Step 9 - Evaluation signals',
    title: 'Compare strengths, gaps, seniority, and watchouts.',
    body: 'The evaluation grid keeps positive signals and risks side by side so the user can review a balanced, evidence-backed hiring assessment.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'candidate-review-handoff',
    path: '/app/workflows/candidate-review',
    selector: '[data-tour="candidate-review-handoff"]',
    eyebrow: 'Step 10 - Handoff',
    title: 'Publish or inspect artifacts only after the review is ready.',
    body: 'The final section keeps Trello, Notion, deck artifacts, and export files downstream from the grounded review.',
    placement: 'above',
    scrollBlock: 'center',
  },
];

const DECK_CENTER_TOUR_STEPS: TourStep[] = [
  {
    id: 'deck-center-header',
    path: '/app/deck-center',
    selector: '[data-tour="deck-center-header"]',
    eyebrow: 'Step 1 - Deck center',
    title: 'Start with the generated artifact catalog.',
    body: 'Deck Center is where generated presentations, review sidecars, preview assets, and registry metadata become easy to inspect and download.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'deck-center-metrics',
    path: '/app/deck-center',
    selector: '[data-tour="deck-center-metrics"]',
    eyebrow: 'Step 2 - Artifact readiness',
    title: 'Check artifact readiness before opening files.',
    body: 'These cards summarize how many artifacts exist, how many are ready, which need review, and how many preview assets are available.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'deck-center-filters',
    path: '/app/deck-center',
    selector: '[data-tour="deck-center-filters"]',
    eyebrow: 'Step 3 - Filters',
    title: 'Filter by deck, status, or workflow.',
    body: 'Search and filters keep the page focused on share-ready decks instead of forcing the user to scan raw export metadata.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'deck-center-list',
    path: '/app/deck-center',
    selector: '[data-tour="deck-center-list"]',
    eyebrow: 'Step 4 - Artifact list',
    title: 'Choose the generated output to inspect.',
    body: 'Each card summarizes the deck title, workflow source, readiness, slide count, preview count, and available files.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'deck-center-detail',
    path: '/app/deck-center',
    selector: '[data-tour="deck-center-detail"]',
    eyebrow: 'Step 5 - Artifact detail',
    title: 'Inspect the selected deck package.',
    body: 'The detail panel collects primary files, preview slides, readiness notes, and registry assets for the selected artifact.',
    placement: 'left',
    scrollBlock: 'center',
  },
];

const RUN_HISTORY_TOUR_STEPS: TourStep[] = [
  {
    id: 'run-history-header',
    path: '/app/history',
    selector: '[data-tour="run-history-header"]',
    eyebrow: 'Step 1 - Run history',
    title: 'Start with the persisted execution registry.',
    body: 'Run History shows what the workflows have actually executed, including status, source documents, duration, result sections, artifacts, and rerun controls.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'run-history-metrics',
    path: '/app/history',
    selector: '[data-tour="run-history-metrics"]',
    eyebrow: 'Step 2 - Registry health',
    title: 'Read the run totals before opening a log.',
    body: 'These cards summarize total executions, completed runs, warnings, and errors so the operator can see whether the demo history is healthy at a glance.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'run-history-filters',
    path: '/app/history',
    selector: '[data-tour="run-history-filters"]',
    eyebrow: 'Step 3 - Filters',
    title: 'Keep the registry usable with targeted filters.',
    body: 'Search, status, workflow, and time-window filters help avoid a raw log dump and keep the user focused on the run they want to inspect.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'run-history-list',
    path: '/app/history',
    selector: '[data-tour="run-history-list"]',
    eyebrow: 'Step 4 - Run list',
    title: 'Choose a run from the ordered history.',
    body: 'Each row keeps the workflow label, documents, timestamp, duration, finding count, and recommendation visible before the detail panel changes.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'run-history-detail',
    path: '/app/history',
    selector: '[data-tour="run-history-detail"]',
    eyebrow: 'Step 5 - Detail and rerun',
    title: 'Inspect the selected run before rerunning or exporting.',
    body: 'The detail panel collects the summary, source counts, artifacts, deliveries, request payload, response payload, and rerun button so run operations stay auditable.',
    tip: 'Finish here when you are ready to move from product outputs into system configuration.',
    placement: 'left',
    scrollBlock: 'center',
  },
];

const RUNTIME_CONTROLS_TOUR_STEPS: TourStep[] = [
  {
    id: 'runtime-controls-header',
    path: '/app/settings/runtime',
    selector: '[data-tour="runtime-controls-header"]',
    eyebrow: 'Step 1 - Runtime controls',
    title: 'Start with the active execution path.',
    body: 'Runtime Controls is for the live route the app will use right now: generation, retrieval, document processing, and observed provider fit.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'runtime-controls-summary',
    path: '/app/settings/runtime',
    selector: '[data-tour="runtime-controls-summary"]',
    eyebrow: 'Step 2 - Active summary',
    title: 'Confirm the effective runtime profile.',
    body: 'This summary shows the active profile, provider connection, model, embedding stack, retrieval posture, and document preset before any edits are made.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'runtime-controls-generation',
    path: '/app/settings/runtime',
    selector: '[data-tour="runtime-controls-generation"]',
    eyebrow: 'Step 3 - Generation controls',
    title: 'Edit the model route that generates workflow output.',
    body: 'Generation controls choose the primary provider, model, context window, decoding behavior, and prompt posture.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'runtime-controls-retrieval',
    path: '/app/settings/runtime',
    selector: '[data-tour="runtime-controls-retrieval"]',
    eyebrow: 'Step 4 - Retrieval and ranking',
    title: 'Tune how documents become grounded context.',
    body: 'This section controls the embedding connection, embedding model, top-k, chunk sizing, overlap, rerank pool, lexical weight, and reranker toggle.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'runtime-controls-doc-processing',
    path: '/app/settings/runtime',
    selector: '[data-tour="runtime-controls-doc-processing"]',
    eyebrow: 'Step 5 - Document processing',
    title: 'Check extraction, OCR, and VLM behavior.',
    body: 'Document processing determines how PDFs are extracted, when OCR recovery is used, and whether VLM enhancement participates in complex layouts.',
    placement: 'below',
    scrollBlock: 'start',
    panelWidth: 410,
    forcePlacement: true,
    compactPanel: true,
  },
];

const PREFERENCES_TOUR_STEPS: TourStep[] = [
  {
    id: 'preferences-header',
    path: '/app/settings/preferences',
    selector: '[data-tour="preferences-header"]',
    eyebrow: 'Step 1 - Preferences',
    title: 'Start with saved workspace configuration.',
    body: 'Preferences stores provider connections, runtime profiles, and operator preferences. Runtime Controls stays focused on the active execution route.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'preferences-metrics',
    path: '/app/settings/preferences',
    selector: '[data-tour="preferences-metrics"]',
    eyebrow: 'Step 2 - Configuration coverage',
    title: 'Check what the workspace already knows.',
    body: 'These cards count provider connections, healthy connections, and saved runtime profiles so setup coverage is visible immediately.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'preferences-summary',
    path: '/app/settings/preferences',
    selector: '[data-tour="preferences-summary"]',
    eyebrow: 'Step 3 - Saved defaults summary',
    title: 'Understand the active profile, export default, and credential posture.',
    body: 'This compact summary keeps the most important saved settings readable without opening every provider or profile card.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'preferences-connections',
    path: '/app/settings/preferences',
    selector: '[data-tour="preferences-connections"]',
    eyebrow: 'Step 4 - Provider connections',
    title: 'Review provider health and credential handling.',
    body: 'Connection cards show endpoint mode, capabilities, authentication posture, preferred model, last check, and a safe test action without exposing secrets.',
    placement: 'left',
    scrollBlock: 'center',
    panelWidth: 390,
    compactPanel: true,
  },
  {
    id: 'preferences-profiles',
    path: '/app/settings/preferences',
    selector: '[data-tour="preferences-profiles"]',
    eyebrow: 'Step 5 - Runtime profiles',
    title: 'Manage saved profile presets.',
    body: 'Profiles package model route, execution policy, quality posture, retrieval strategy, document preset, and output budget into reusable presets.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'preferences-operator',
    path: '/app/settings/preferences',
    selector: '[data-tour="preferences-operator"]',
    eyebrow: 'Step 6 - Operator preferences',
    title: 'Finish the product configuration layer.',
    body: 'Operator preferences keep source badges, export format, and benchmark baseline visible as the final saved workspace defaults.',
    tip: 'Finish here to keep the product tour ending cleanly. A Continue tour cue will appear beside AI Lab Overview when you want to enter the more technical observability layer.',
    placement: 'above',
    scrollBlock: 'center',
  },
];

const LAB_OVERVIEW_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-overview-header',
    path: '/app/lab/overview',
    selector: '[data-tour="lab-overview-header"]',
    eyebrow: 'Step 1 - AI Lab handoff',
    title: 'Move from product flow to the technical layer.',
    body: 'The product walkthrough is complete. AI Lab is the operator view: it explains runtime health, quality signals, alerts, experiments, and auditability behind the product experience.',
    tip: 'This tour is intentionally optional. Start it when you want to show what is happening behind the scenes instead of continuing the end-user product flow.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'lab-overview-status-strip',
    path: '/app/lab/overview',
    selector: '[data-tour="lab-overview-status-strip"]',
    eyebrow: 'Step 2 - Operating status',
    title: 'Start with the health strip.',
    body: 'This strip separates the high-level AI Lab posture from the rest of the page: live state, degraded state, warnings, and readiness are visible before deeper diagnostics.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-overview-metrics',
    path: '/app/lab/overview',
    selector: '[data-tour="lab-overview-metrics"]',
    eyebrow: 'Step 3 - KPI snapshot',
    title: 'Read the compact lab KPIs.',
    body: 'These cards summarize the technical operating state without forcing the user to inspect every detailed page first.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-overview-signals',
    path: '/app/lab/overview',
    selector: '[data-tour="lab-overview-signals"]',
    eyebrow: 'Step 4 - Signals and attention',
    title: 'See what deserves deeper inspection.',
    body: 'The signal area highlights health, warnings, pressure, and review context. It is the bridge between a product demo and a technical operator diagnosis.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-overview-surface-map',
    path: '/app/lab/overview',
    selector: '[data-tour="lab-overview-surface-map"]',
    eyebrow: 'Step 5 - Lab surface map',
    title: 'Choose the next technical view.',
    body: 'The surface map points to specialist pages. Finish here, then use Continue tour beside Runtime & Observability to go deeper into runtime diagnostics.',
    placement: 'above',
    scrollBlock: 'center',
  },
];

const LAB_RUNTIME_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-runtime-header',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-header"]',
    eyebrow: 'Step 1 - Runtime observability',
    title: 'Inspect runtime behavior as an operator.',
    body: 'Runtime & Observability explains what the system is doing after product workflows run: providers, latency, retrieval, cost, coverage, and trace pressure.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'lab-runtime-metrics',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-metrics"]',
    eyebrow: 'Step 2 - Runtime KPIs',
    title: 'Check runtime health before diagnostics.',
    body: 'These top cards give a fast read on success rate, p95 latency, review pressure, token volume, empty retrievals, and recent throughput.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-summary-cards',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-summary-cards"]',
    eyebrow: 'Step 3 - Summary cards',
    title: 'Separate headline signals from deeper charts.',
    body: 'These cards summarize dominant provider, typical grounding usage, grounding variance, and cost visibility before you open the detailed diagnostic panels.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-config',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-config"]',
    eyebrow: 'Step 4 - Active configuration',
    title: 'Verify generation and retrieval settings together.',
    body: 'Generation Configuration and Retrieval Configuration belong together because they explain the active route: provider, model, embedding strategy, chunking posture, and retrieval parameters.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-grounding',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-grounding"]',
    eyebrow: 'Step 5 - Grounded evidence usage',
    title: 'Explain evidence usage without confusing it with context-window pressure.',
    body: 'This card shows how much of the selected evidence packet recent runs actually used. A high value means broad evidence consumption, not necessarily that the LLM prompt window failed.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-latency',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-latency"]',
    eyebrow: 'Step 6 - Latency breakdown',
    title: 'Look at where runtime time is spent.',
    body: 'This chart separates stage timing so you can tell whether retrieval, generation, parsing, or another stage is driving the delay.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-cost-simulation',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-cost-simulation"]',
    eyebrow: 'Step 7 - Cost simulation',
    title: 'Model expected spend without changing real cost telemetry.',
    body: 'The cost simulator lets an operator enter provider-style token prices and compare simulated spend against observed token usage.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-trend',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-trend"]',
    eyebrow: 'Step 8 - Recent product run trend',
    title: 'Read the runtime trend over recent runs.',
    body: 'This graph shows latency and grounding coverage over time. Use it to spot spikes and then confirm whether the issue was runtime delay or over-broad evidence usage.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-retrieval-cost',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-retrieval-cost"]',
    eyebrow: 'Step 9 - Retrieval and cost signals',
    title: 'Check retrieval health beside token accounting.',
    body: 'This card pairs empty retrievals, retrieved chunks, prompt truncation, tokens, cost, and priced-run coverage so retrieval quality and spend are not treated as separate mysteries.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-vector-diagnostics',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-vector-diagnostics"]',
    eyebrow: 'Step 10 - Vector backend and diagnostics',
    title: 'Verify the retrieval backend health.',
    body: 'This card explains the vector backend, index status, retrieval diagnostics, and related runtime posture. It is the technical check for whether grounding infrastructure is healthy.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-trace-watchlist',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-trace-watchlist"]',
    eyebrow: 'Step 11 - Recent trace watchlist',
    title: 'Inspect the specific traces that deserve attention.',
    body: 'The watchlist shows recent product-relevant traces, including provider, model, latency, token count, grounding coverage, sources, and review/error status.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-runtime-failure-modes',
    path: '/app/lab/runtime',
    selector: '[data-tour="lab-runtime-failure-modes"]',
    eyebrow: 'Step 12 - Failure modes and watchouts',
    title: 'Finish with recurring failure patterns.',
    body: 'These watchouts summarize repeated issues across the recent window. Finish here, then continue into Document Experiments when you want to probe grounded behavior directly.',
    placement: 'top-left',
    scrollBlock: 'center',
    panelWidth: 360,
    forcePlacement: true,
    compactPanel: true,
  },
];

const LAB_DOCUMENT_EXPERIMENTS_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-document-experiments-header',
    path: '/app/lab/chat',
    selector: '[data-tour="lab-document-experiments-header"]',
    eyebrow: 'Step 1 - Document experiments',
    title: 'Probe grounded behavior outside the product workflow.',
    body: 'Document Experiments is the technical RAG playground: ask questions, inspect source behavior, test selected documents, and preserve useful traces for debugging.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: -18 },
  },
  {
    id: 'lab-document-experiments-chat',
    path: '/app/lab/chat',
    selector: '[data-tour="lab-document-experiments-main-panel"]',
    eyebrow: 'Step 2 - Chat transcript',
    title: 'Read the grounded conversation here.',
    body: 'The main pane is where user questions, assistant answers, grounding badges, and the prompt entry sit together for the diagnostic conversation.',
    placement: 'right',
    scrollBlock: 'center',
    panelWidth: 280,
    compactPanel: true,
  },
  {
    id: 'lab-document-experiments-prompt',
    path: '/app/lab/chat',
    selector: '[data-tour="lab-document-experiments-prompt"]',
    eyebrow: 'Step 3 - Prompt entry',
    title: 'Ask the next bounded diagnostic question.',
    body: 'The prompt bar lives under the chat. Operators use it to test a specific retrieval or answer-quality hypothesis against the selected documents.',
    placement: 'above',
    scrollBlock: 'end',
    panelWidth: 420,
    forcePlacement: true,
    compactPanel: true,
    spotlightOffset: { x: -8, y: -6, width: 16, height: 12 },
  },
  {
    id: 'lab-document-experiments-sessions',
    path: '/app/lab/chat',
    selector: '[data-tour="lab-document-experiments-sessions"]',
    eyebrow: 'Step 4 - Sessions',
    title: 'Switch between persisted experiment sessions.',
    body: 'Sessions keep previous chat traces available, so you can compare experiments without losing the context that created them.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-document-experiments-documents',
    path: '/app/lab/chat',
    selector: '[data-tour="lab-document-experiments-documents"]',
    eyebrow: 'Step 5 - Selected documents',
    title: 'Control which documents ground the next answer.',
    body: 'This card determines the evidence set for the next chat turn. It is separate from the transcript so operators can see exactly what context is being tested.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-document-experiments-activity',
    path: '/app/lab/chat',
    selector: '[data-tour="lab-document-experiments-activity"]',
    eyebrow: 'Step 6 - Recent activity',
    title: 'Finish with the session activity trail.',
    body: 'Recent activity shows persisted chat events. Finish here, then continue into Workflow Inspector for trace-level workflow auditability.',
    placement: 'left',
    scrollBlock: 'center',
  },
];

const LAB_WORKFLOW_INSPECTOR_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-workflow-inspector-header',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-header"]',
    eyebrow: 'Step 1 - Workflow inspector',
    title: 'Connect product tasks to technical execution.',
    body: 'Workflow Inspector shows selected documents, task instructions, routing decisions, confidence, guardrail triggers, sources, and persisted traces.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'lab-workflow-inspector-metrics',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-metrics"]',
    eyebrow: 'Step 2 - Inspector KPIs',
    title: 'Read the persisted inspector history first.',
    body: 'These metrics show total cases, review pressure, confidence, blockers, and failures so the operator knows whether the recent inspector window is healthy.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-summary',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-summary"]',
    eyebrow: 'Step 3 - Inspector summary cards',
    title: 'Separate tracked tasks, recent window, mode mix, and review pressure.',
    body: 'These small cards explain the shape of the captured inspector data before you run a new task or inspect details.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-task-selection',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-task-selection"]',
    eyebrow: 'Step 4 - Task selection',
    title: 'Choose the workflow task to reproduce.',
    body: 'Pick the product task you want to inspect. Each task carries its recent trace count so the operator can see whether there is enough evidence for that workflow.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-documents',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-documents"]',
    eyebrow: 'Step 5 - Document selection',
    title: 'Select the exact document inputs.',
    body: 'Document Review uses one primary document. Policy Comparison requires a distinct pair, so this area keeps the two document inputs explicit.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-instructions',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-instructions"]',
    eyebrow: 'Step 6 - Bounded instructions',
    title: 'Keep the diagnostic prompt controlled.',
    body: 'Instructions are capped so the public demo stays usable and the trace remains readable. This makes Workflow Inspector useful for reproducible tests rather than arbitrary long prompts.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-trace-posture',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-trace-posture"]',
    eyebrow: 'Step 7 - Live trace posture',
    title: 'Check routing and review pressure before executing.',
    body: 'This card summarizes mode mix and review reasons so the operator can understand current trace posture before pressing Execute Task.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-audit',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-audit"]',
    eyebrow: 'Step 8 - Audit output',
    title: 'Inspect the current run output.',
    body: 'The audit output explains the run result, routing trail, review reasons, execution metadata, and source-backed behavior without merging it with the input controls.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-cases',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-case-history-start"]',
    fallbackSelector: '[data-tour="lab-workflow-inspector-cases"]',
    eyebrow: 'Step 9 - Case history',
    title: 'Compare against recent persisted cases.',
    body: 'Recent cases help explain whether a behavior is isolated or part of a broader pattern across workflow executions.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 390,
    forcePlacement: true,
    compactPanel: true,
  },
  {
    id: 'lab-workflow-inspector-task-health',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-task-health"]',
    eyebrow: 'Step 10 - Task health',
    title: 'Read task health separately from individual runs.',
    body: 'Task Health aggregates recent workflow behavior so operators can see review rate, latency, status, and recency at the task level.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-workflow-inspector-latest-runs',
    path: '/app/lab/workflow-inspector',
    selector: '[data-tour="lab-workflow-inspector-latest-runs"]',
    eyebrow: 'Step 11 - Latest live runs',
    title: 'Finish with the most recent execution evidence.',
    body: 'Latest Live Runs links the technical audit view back to actual workflow activity. Finish here, then continue into Benchmarks when you want model and strategy comparison evidence.',
    placement: 'left',
    scrollBlock: 'center',
  },
];

const LAB_BENCHMARKS_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-benchmarks-header',
    path: '/app/lab/benchmarks',
    selector: '[data-tour="lab-benchmarks-header"]',
    eyebrow: 'Step 1 - Benchmarks',
    title: 'Compare models and strategies with recorded evidence.',
    body: 'Benchmarks is where the technical tour moves from live runtime traces into measured comparisons: runs, scored models, scenarios, latency, fit, groundedness, and retrieval strategy evidence.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -12, width: 20, height: 8 },
  },
  {
    id: 'lab-benchmarks-metrics',
    path: '/app/lab/benchmarks',
    selector: '[data-tour="lab-benchmarks-metrics"]',
    eyebrow: 'Step 2 - Benchmark KPIs',
    title: 'Start with the recorded benchmark counts.',
    body: 'These metrics show how much comparison evidence exists: recorded runs, tested models, scored models, benchmark scenarios, best fit, and fastest latency.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-benchmarks-coverage',
    path: '/app/lab/benchmarks',
    selector: '[data-tour="lab-benchmarks-coverage"]',
    eyebrow: 'Step 3 - Coverage and posture',
    title: 'Understand benchmark coverage before ranking models.',
    body: 'These cards explain provider coverage, top scored provider, benchmark freshness/posture, and how many benchmark bundles were merged into this surface.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-benchmarks-highlights',
    path: '/app/lab/benchmarks',
    selector: '[data-tour="lab-benchmarks-highlights"]',
    fallbackSelector: '[data-tour="lab-benchmarks-tabs"]',
    eyebrow: 'Step 4 - Leaderboard highlights',
    title: 'Use highlights for the fastest benchmark story.',
    body: 'Highlights call out the most useful benchmark takeaways before the operator opens the detailed tabs.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-benchmarks-tabs',
    path: '/app/lab/benchmarks',
    selector: '[data-tour="lab-benchmarks-tabs"]',
    eyebrow: 'Step 5 - Benchmark views',
    title: 'Switch between leaderboard, tradeoffs, cards, profiles, and retrieval strategy views.',
    body: 'The tabs keep each comparison mode separate, so a benchmark story can focus on rankings, latency/fit tradeoffs, individual model cards, prompt profiles, or retrieval observations.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-benchmarks-leaderboard',
    path: '/app/lab/benchmarks',
    selector: '[data-tour="lab-benchmarks-leaderboard-row"]',
    fallbackSelector: '[data-tour="lab-benchmarks-leaderboard"]',
    eyebrow: 'Step 6 - Model leaderboard',
    title: 'Finish with the ranked model evidence.',
    body: 'The top leaderboard rows show provider, family, latency, adherence, groundedness, and fit before you continue into Evals & Diagnosis for quality and regression analysis.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 430,
    forcePlacement: true,
    compactPanel: true,
  },
];

const LAB_EVALS_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-evals-header',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-header"]',
    eyebrow: 'Step 1 - Evals and diagnosis',
    title: 'Move from benchmark comparison into quality control.',
    body: 'Evals & Diagnosis explains whether active product workflows are healthy, where quality has regressed, and which cases need investigation.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'lab-evals-metrics',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-metrics"]',
    eyebrow: 'Step 2 - Eval KPIs',
    title: 'Separate historical baseline from live telemetry.',
    body: 'These cards show historical pass rate, historical cases, live pass rate, live runs, and active task coverage so quality is not judged from a single number.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-evals-coverage',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-coverage"]',
    eyebrow: 'Step 3 - Coverage context',
    title: 'Check observed workflows and eval coverage.',
    body: 'These cards explain workflow coverage, historical window, live telemetry window, and task gaps before looking at individual failures.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-evals-distribution',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-distribution"]',
    eyebrow: 'Step 4 - Verdict distribution',
    title: 'Read pass, warn, and fail distribution.',
    body: 'The distribution charts show how historical suites and live workflow evals are split across pass, warning, and failure outcomes.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-evals-suite-leaderboard',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-suite-leaderboard"]',
    fallbackSelector: '[data-tour="lab-evals-investigate"]',
    eyebrow: 'Step 5 - Historical suite leaderboard',
    title: 'Read baseline quality separately.',
    body: 'The suite leaderboard summarizes the retained historical baseline so it does not get mixed into the failure triage card.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 410,
    compactPanel: true,
  },
  {
    id: 'lab-evals-investigate',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-investigate-first"]',
    fallbackSelector: '[data-tour="lab-evals-investigate"]',
    eyebrow: 'Step 6 - Investigate first',
    title: 'Prioritize failures before broad breakdowns.',
    body: 'Investigate First keeps the concrete failing cases separate from aggregate baseline quality, so operator review starts with the most actionable evidence.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 410,
    compactPanel: true,
  },
  {
    id: 'lab-evals-provider-breakdown',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-provider-breakdown"]',
    fallbackSelector: '[data-tour="lab-evals-breakdowns"]',
    eyebrow: 'Step 7 - Provider breakdown',
    title: 'Locate provider-specific quality clusters.',
    body: 'Provider slices show whether quality issues concentrate around a specific model or provider family.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 390,
    compactPanel: true,
  },
  {
    id: 'lab-evals-task-coverage',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-task-coverage"]',
    fallbackSelector: '[data-tour="lab-evals-breakdowns"]',
    eyebrow: 'Step 8 - Historical task coverage',
    title: 'Check which tasks are covered.',
    body: 'Task coverage explains where the retained eval baseline has enough task evidence and where coverage is still thin.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 390,
    compactPanel: true,
  },
  {
    id: 'lab-evals-attention-queue',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-attention-queue"]',
    fallbackSelector: '[data-tour="lab-evals-breakdowns"]',
    eyebrow: 'Step 9 - Product attention queue',
    title: 'Inspect the current attention queue.',
    body: 'The product attention queue lists the live or historical cases that should stay visible for operator follow-up.',
    placement: 'left',
    scrollBlock: 'center',
    panelWidth: 390,
    compactPanel: true,
  },
  {
    id: 'lab-evals-recent-cases',
    path: '/app/lab/evals',
    selector: '[data-tour="lab-evals-recent-cases-start"]',
    fallbackSelector: '[data-tour="lab-evals-recent-cases"]',
    eyebrow: 'Step 10 - Recent eval cases',
    title: 'Finish with the row-level evidence.',
    body: 'The recent eval header and first rows are the audit trail behind the quality summary. Finish here, then continue into Experiments & Artifacts to inspect persisted bundles and evidence.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 390,
    forcePlacement: true,
    compactPanel: true,
  },
];

const LAB_ARTIFACTS_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-artifacts-header',
    path: '/app/lab/artifacts',
    selector: '[data-tour="lab-artifacts-header"]',
    eyebrow: 'Step 1 - Experiments and artifacts',
    title: 'Inspect persisted technical evidence.',
    body: 'Experiments & Artifacts shows export bundles, workflow-linked evidence, run registries, captures, diagnostics, and artifact files that explain current behavior.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 34 },
  },
  {
    id: 'lab-artifacts-metrics',
    path: '/app/lab/artifacts',
    selector: '[data-tour="lab-artifacts-metrics"]',
    eyebrow: 'Step 2 - Artifact KPIs',
    title: 'Start with bundle and capture posture.',
    body: 'These metrics show export bundle count, ready bundles, attention items, and how many workflow runs are linked to artifacts.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-artifacts-registry-summary',
    path: '/app/lab/artifacts',
    selector: '[data-tour="lab-artifacts-registry-summary"]',
    eyebrow: 'Step 3 - Registry summary',
    title: 'Understand chat, workflow, and capture coverage.',
    body: 'These cards summarize persisted chat sessions, product workflow runs, latest linked artifact, and capture posture before you open detailed registries.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-artifacts-run-registry',
    path: '/app/lab/artifacts',
    selector: '[data-tour="lab-artifacts-run-registry"]',
    eyebrow: 'Step 4 - Run registry',
    title: 'Link sessions, workflow runs, and artifacts.',
    body: 'The run registry shows the latest chat session, latest product workflow run, and latest linked workflow artifact in one focused area.',
    placement: 'right',
    scrollBlock: 'center',
  },
  {
    id: 'lab-artifacts-recent-bundles',
    path: '/app/lab/artifacts',
    selector: '[data-tour="lab-artifacts-recent-bundles"]',
    eyebrow: 'Step 5 - Recent bundles',
    title: 'Review the latest product-visible bundles.',
    body: 'Recent Bundles shows captures with workflow label, export kind, previews, issues, warnings, and assets so output evidence stays inspectable.',
    placement: 'left',
    scrollBlock: 'center',
  },
  {
    id: 'lab-artifacts-diagnostics',
    path: '/app/lab/artifacts',
    selector: '[data-tour="lab-artifacts-diagnostics"]',
    eyebrow: 'Step 6 - Processing diagnostics',
    title: 'Check artifact processing health.',
    body: 'Diagnostics explain whether the current workspace has healthy bundle processing, capture linkage, and metadata availability.',
    placement: 'above',
    scrollBlock: 'center',
  },
  {
    id: 'lab-artifacts-explorer',
    path: '/app/lab/artifacts',
    selector: '[data-tour="lab-artifacts-explorer-start"]',
    fallbackSelector: '[data-tour="lab-artifacts-explorer"]',
    eyebrow: 'Step 7 - Artifact explorer',
    title: 'Finish with the explorable artifact list.',
    body: 'The explorer header, first category summary, and first artifact rows show how persisted evidence can be opened and filtered without spotlighting the entire explorer.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 390,
    forcePlacement: true,
    compactPanel: true,
  },
];

const LAB_EVIDENCEOPS_TOUR_STEPS: TourStep[] = [
  {
    id: 'lab-evidenceops-header',
    path: '/app/lab/evidenceops',
    selector: '[data-tour="lab-evidenceops-header"]',
    eyebrow: 'Step 1 - EvidenceOps / MCP',
    title: 'Finish the AI Lab with operations and governance.',
    body: 'EvidenceOps / MCP is the operational console: local MCP tool health, backlog actions, automated operations, repository readiness, telemetry, and search.',
    placement: 'below',
    scrollBlock: 'start',
    spotlightOffset: { x: -10, y: -16, width: 20, height: 20 },
  },
  {
    id: 'lab-evidenceops-metrics',
    path: '/app/lab/evidenceops',
    selector: '[data-tour="lab-evidenceops-metrics"]',
    eyebrow: 'Step 2 - EvidenceOps KPIs',
    title: 'Read MCP tools, backlog, ownership, and sync state.',
    body: 'These top cards show local MCP tools, open backlog, recent open items, unassigned queue, and last sync time.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-evidenceops-repository',
    path: '/app/lab/evidenceops',
    selector: '[data-tour="lab-evidenceops-repository"]',
    eyebrow: 'Step 3 - Repository posture',
    title: 'Check drift, footprint, and operation mix.',
    body: 'These cards show whether the repository changed, how large the visible corpus is, and what kind of operations have been happening recently.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-evidenceops-delivery',
    path: '/app/lab/evidenceops',
    selector: '[data-tour="lab-evidenceops-delivery"]',
    eyebrow: 'Step 4 - Connected delivery targets',
    title: 'Separate external delivery surfaces from local MCP tools.',
    body: 'This strip verifies external delivery targets such as Nextcloud, Trello, and Notion without mixing them into the local MCP-console tool inventory.',
    placement: 'top-left',
    scrollBlock: 'center',
    panelWidth: 360,
    forcePlacement: true,
    compactPanel: true,
  },
  {
    id: 'lab-evidenceops-tabs',
    path: '/app/lab/evidenceops',
    selector: '[data-tour="lab-evidenceops-tabs"]',
    eyebrow: 'Step 5 - Operational tabs',
    title: 'Use each tab for a specific operations question.',
    body: 'Tools, Open Backlog, Auto Operations, Timeline, Telemetry, Readiness, and Search are kept separate so governance does not feel like one large undifferentiated panel.',
    placement: 'below',
    scrollBlock: 'center',
  },
  {
    id: 'lab-evidenceops-tools',
    path: '/app/lab/evidenceops',
    selector: '[data-tour="lab-evidenceops-tools-start"]',
    fallbackSelector: '[data-tour="lab-evidenceops-tools"]',
    eyebrow: 'Step 6 - Local MCP tools',
    title: 'Inspect the actual local MCP-console tools.',
    body: 'The local MCP-console heading and first tool rows list repository, action, and worklog operations exposed by the local EvidenceOps server. The remaining tabs stay available for readiness, telemetry, timeline, backlog actions, and repository search.',
    placement: 'below',
    scrollBlock: 'center',
    panelWidth: 390,
    forcePlacement: true,
    compactPanel: true,
  },
];

const TOUR_STEPS_BY_KIND: Record<ActiveTourKind, TourStep[]> = {
  'document-library': DOCUMENT_LIBRARY_TOUR_STEPS,
  workflow: WORKFLOW_TOUR_STEPS,
  'document-review': DOCUMENT_REVIEW_TOUR_STEPS,
  'policy-comparison': POLICY_COMPARISON_TOUR_STEPS,
  'action-plan': ACTION_PLAN_TOUR_STEPS,
  'candidate-review': CANDIDATE_REVIEW_TOUR_STEPS,
  'deck-center': DECK_CENTER_TOUR_STEPS,
  'run-history': RUN_HISTORY_TOUR_STEPS,
  'runtime-controls': RUNTIME_CONTROLS_TOUR_STEPS,
  preferences: PREFERENCES_TOUR_STEPS,
  'lab-overview': LAB_OVERVIEW_TOUR_STEPS,
  'lab-runtime': LAB_RUNTIME_TOUR_STEPS,
  'lab-document-experiments': LAB_DOCUMENT_EXPERIMENTS_TOUR_STEPS,
  'lab-workflow-inspector': LAB_WORKFLOW_INSPECTOR_TOUR_STEPS,
  'lab-benchmarks': LAB_BENCHMARKS_TOUR_STEPS,
  'lab-evals': LAB_EVALS_TOUR_STEPS,
  'lab-artifacts': LAB_ARTIFACTS_TOUR_STEPS,
  'lab-evidenceops': LAB_EVIDENCEOPS_TOUR_STEPS,
};

const TOUR_SEARCH_BY_KIND: Record<ActiveTourKind, string> = {
  'document-library': '?tour=1',
  workflow: '?tour=workflow',
  'document-review': '?tour=document-review',
  'policy-comparison': '?tour=policy-comparison',
  'action-plan': '?tour=action-plan',
  'candidate-review': '?tour=candidate-review',
  'deck-center': '?tour=deck-center',
  'run-history': '?tour=run-history',
  'runtime-controls': '?tour=runtime-controls',
  preferences: '?tour=preferences',
  'lab-overview': '?tour=lab-overview',
  'lab-runtime': '?tour=lab-runtime',
  'lab-document-experiments': '?tour=lab-document-experiments',
  'lab-workflow-inspector': '?tour=lab-workflow-inspector',
  'lab-benchmarks': '?tour=lab-benchmarks',
  'lab-evals': '?tour=lab-evals',
  'lab-artifacts': '?tour=lab-artifacts',
  'lab-evidenceops': '?tour=lab-evidenceops',
};


const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const TOUR_SAFE_TOP = 92;
const TOUR_SAFE_PADDING = 18;
const TOUR_PANEL_GAP = 16;
const TOUR_SPOTLIGHT_PADDING = 10;
const TOUR_MIN_PANEL_VISIBLE_HEIGHT = 128;

function getSafeBounds() {
  return {
    top: TOUR_SAFE_TOP,
    left: TOUR_SAFE_PADDING,
    right: window.innerWidth - TOUR_SAFE_PADDING,
    bottom: window.innerHeight - TOUR_SAFE_PADDING,
  };
}

function getEstimatedPanelHeight(step: TourStep): number {
  let height = step.compactPanel ? 160 : 196;
  height += Math.min(step.compactPanel ? 72 : 104, Math.ceil(step.body.length / (step.compactPanel ? 96 : 76)) * (step.compactPanel ? 18 : 22));
  if (step.bullets?.length) height += Math.min(226, step.bullets.length * 34 + 24);
  if (step.tip) height += step.compactPanel ? 70 : 86;
  if (step.cta) height += 42;
  if (step.link) height += 36;
  return clamp(height + (step.compactPanel ? 12 : 24), step.compactPanel ? 220 : 260, 600);
}

function getPanelWidth(step: TourStep): number {
  const desiredWidth = step.panelWidth ?? (step.bullets?.length ? 480 : 440);
  return Math.min(desiredWidth, Math.max(280, window.innerWidth - 32));
}

function overlapArea(a: { left: number; top: number; width: number; height: number }, b: { left: number; top: number; width: number; height: number }) {
  const x = Math.max(0, Math.min(a.left + a.width, b.left + b.width) - Math.max(a.left, b.left));
  const y = Math.max(0, Math.min(a.top + a.height, b.top + b.height) - Math.max(a.top, b.top));
  return x * y;
}

function getPlacementOrder(preferred: TourPlacement): TourPlacement[] {
  const base: TourPlacement[] = [preferred, 'below', 'above', 'right', 'left', 'bottom-right', 'bottom-left', 'top-right', 'top-left'];
  return base.filter((placement, index, list) => list.indexOf(placement) === index);
}

function getVisualTarget(rect: TourRect) {
  return {
    left: rect.left - TOUR_SPOTLIGHT_PADDING,
    top: rect.top - TOUR_SPOTLIGHT_PADDING,
    width: rect.width + TOUR_SPOTLIGHT_PADDING * 2,
    height: rect.height + TOUR_SPOTLIGHT_PADDING * 2,
  };
}

function buildPanelCandidate(rect: TourRect, width: number, height: number, placement: TourPlacement): PanelCandidate {
  const safe = getSafeBounds();
  const target = getVisualTarget(rect);
  const targetRight = target.left + target.width;
  const targetBottom = target.top + target.height;
  const middleLeft = rect.left + rect.width / 2 - width / 2;
  const viewportHeight = Math.max(TOUR_MIN_PANEL_VISIBLE_HEIGHT, safe.bottom - safe.top);
  const sideHeight = Math.min(height, viewportHeight);
  const middleTop = rect.top + rect.height / 2 - sideHeight / 2;

  let candidate: PanelCandidate;

  if (placement === 'below') {
    const top = targetBottom + TOUR_PANEL_GAP;
    const maxHeight = Math.max(0, safe.bottom - top);
    candidate = {
      placement,
      left: clamp(middleLeft, safe.left, Math.max(safe.left, safe.right - width)),
      top,
      maxHeight,
      visibleHeight: Math.min(height, maxHeight),
    };
  } else if (placement === 'above') {
    const bottom = target.top - TOUR_PANEL_GAP;
    const maxHeight = Math.max(0, bottom - safe.top);
    const visibleHeight = Math.min(height, maxHeight);
    candidate = {
      placement,
      left: clamp(middleLeft, safe.left, Math.max(safe.left, safe.right - width)),
      top: bottom - visibleHeight,
      maxHeight,
      visibleHeight,
    };
  } else if (placement === 'right') {
    candidate = {
      placement,
      left: targetRight + TOUR_PANEL_GAP,
      top: clamp(middleTop, safe.top, Math.max(safe.top, safe.bottom - sideHeight)),
      visibleHeight: sideHeight,
    };
  } else if (placement === 'left') {
    candidate = {
      placement,
      left: target.left - width - TOUR_PANEL_GAP,
      top: clamp(middleTop, safe.top, Math.max(safe.top, safe.bottom - sideHeight)),
      visibleHeight: sideHeight,
    };
  } else if (placement === 'top-right') {
    candidate = { placement, left: safe.right - width, top: safe.top, visibleHeight: sideHeight };
  } else if (placement === 'top-left') {
    candidate = { placement, left: safe.left, top: safe.top, visibleHeight: sideHeight };
  } else if (placement === 'bottom-right') {
    candidate = { placement, left: safe.right - width, top: safe.bottom - sideHeight, visibleHeight: sideHeight };
  } else {
    candidate = { placement, left: safe.left, top: safe.bottom - sideHeight, visibleHeight: sideHeight };
  }

  const visibleHeight = Math.max(0, candidate.visibleHeight ?? height);
  const panel = { left: candidate.left, top: candidate.top, width, height: visibleHeight };
  const overflow = candidateOverflow(candidate, width, visibleHeight);
  const collision = visibleHeight > 0 ? overlapArea(panel, target) : Number.POSITIVE_INFINITY;
  const fits = overflow === 0 && collision === 0 && visibleHeight >= Math.max(TOUR_MIN_PANEL_VISIBLE_HEIGHT, height - 1);

  return { ...candidate, overflow, collision, fits, visibleHeight };
}

function candidateOverflow(candidate: PanelCandidate, width: number, height: number) {
  const safe = getSafeBounds();
  return Math.max(0, safe.left - candidate.left)
    + Math.max(0, candidate.left + width - safe.right)
    + Math.max(0, safe.top - candidate.top)
    + Math.max(0, candidate.top + height - safe.bottom);
}

function clampCandidate(candidate: PanelCandidate, width: number, height: number): PanelCandidate {
  const safe = getSafeBounds();
  return {
    ...candidate,
    left: clamp(candidate.left, safe.left, Math.max(safe.left, safe.right - width)),
    top: clamp(candidate.top, safe.top, Math.max(safe.top, safe.bottom - height)),
  };
}

function getPanelStyle(rect: TourRect | null, step: TourStep, measuredHeight?: number | null): CSSProperties {
  const width = getPanelWidth(step);
  const estimatedHeight = measuredHeight || getEstimatedPanelHeight(step);

  if (!rect) return { width, left: `calc(50vw - ${width / 2}px)`, top: '18vh' };

  const safe = getSafeBounds();
  const preferred = step.placement || 'below';
  const orderedPlacements = getPlacementOrder(preferred);
  const ranked = orderedPlacements
    .map((placement, index) => {
      const candidate = buildPanelCandidate(rect, width, estimatedHeight, placement);
      const distancePenalty =
        placement === 'above'
          ? Math.abs((candidate.top + (candidate.visibleHeight ?? estimatedHeight) + TOUR_PANEL_GAP) - (rect.top - TOUR_SPOTLIGHT_PADDING))
          : placement === 'below'
            ? Math.abs(candidate.top - (rect.top + rect.height + TOUR_SPOTLIGHT_PADDING + TOUR_PANEL_GAP))
            : placement === 'left'
              ? Math.abs((candidate.left + width + TOUR_PANEL_GAP) - (rect.left - TOUR_SPOTLIGHT_PADDING))
              : placement === 'right'
                ? Math.abs(candidate.left - (rect.left + rect.width + TOUR_SPOTLIGHT_PADDING + TOUR_PANEL_GAP))
                : 120;
      const collisionPenalty = (candidate.collision ?? 0) > 0 ? 900000 + (candidate.collision ?? 0) * 120 : 0;
      const overflowPenalty = (candidate.overflow ?? 0) > 0 ? 600000 + (candidate.overflow ?? 0) * 1800 : 0;
      const fitPenalty = candidate.fits ? 0 : 260000;
      const placementPenalty = placement === preferred ? 0 : 600 + index * 60;
      return { candidate, score: placementPenalty + fitPenalty + overflowPenalty + collisionPenalty + distancePenalty };
    })
    .sort((left, right) => left.score - right.score);

  const noOverlap = ranked.find(({ candidate }) => (candidate.collision ?? 1) === 0 && (candidate.overflow ?? 1) === 0 && (candidate.visibleHeight ?? 0) > 0);
  const chosen = (ranked.find(({ candidate }) => candidate.fits) ?? noOverlap ?? ranked[0])?.candidate
    ?? buildPanelCandidate(rect, width, estimatedHeight, preferred);
  const maxHeight = chosen.maxHeight !== undefined ? chosen.maxHeight : Math.max(TOUR_MIN_PANEL_VISIBLE_HEIGHT, safe.bottom - chosen.top);

  return {
    width,
    left: chosen.left,
    top: chosen.top,
    maxHeight: Math.max(1, Math.min(maxHeight, Math.max(1, safe.bottom - chosen.top))),
  };
}

function collectElementRects(selector: string): DOMRect[] {
  return Array.from(document.querySelectorAll(selector))
    .map((element) => (element as HTMLElement).getBoundingClientRect())
    .filter((rect) => rect.width > 0 && rect.height > 0);
}

function normalizeTourRect(rect: TourRect): TourRect {
  const safe = getSafeBounds();
  const left = clamp(rect.left, safe.left, safe.right - 24);
  const right = clamp(rect.left + rect.width, left + 24, safe.right);
  const top = clamp(rect.top, safe.top, safe.bottom - 24);
  const bottom = clamp(rect.top + rect.height, top + 24, safe.bottom);
  return { left, top, width: right - left, height: bottom - top };
}

function getTargetRect(selector: string, fallbackSelector?: string, step?: TourStep): TourRect | null {
  let rects = collectElementRects(selector);
  if (!rects.length && fallbackSelector) rects = collectElementRects(fallbackSelector);
  if (!rects.length) return null;
  const top = Math.min(...rects.map((rect) => rect.top));
  const left = Math.min(...rects.map((rect) => rect.left));
  const right = Math.max(...rects.map((rect) => rect.right));
  const bottom = Math.max(...rects.map((rect) => rect.bottom));
  const normalized = normalizeTourRect({ top, left, width: right - left, height: bottom - top });
  if (!step?.spotlightOffset) return normalized;
  return normalizeTourRect({
    top: normalized.top + (step.spotlightOffset.y ?? 0),
    left: normalized.left + (step.spotlightOffset.x ?? 0),
    width: Math.max(24, normalized.width + (step.spotlightOffset.width ?? 0)),
    height: Math.max(24, normalized.height + (step.spotlightOffset.height ?? 0)),
  });
}

function getRawTargetRect(selector: string, fallbackSelector?: string): TourRect | null {
  let rects = collectElementRects(selector);
  if (!rects.length && fallbackSelector) rects = collectElementRects(fallbackSelector);
  if (!rects.length) return null;
  const top = Math.min(...rects.map((rect) => rect.top));
  const left = Math.min(...rects.map((rect) => rect.left));
  const right = Math.max(...rects.map((rect) => rect.right));
  const bottom = Math.max(...rects.map((rect) => rect.bottom));
  return { top, left, width: right - left, height: bottom - top };
}

function getScrollTarget(selector: string, fallbackSelector?: string): HTMLElement | null {
  return (document.querySelector(selector) || (fallbackSelector ? document.querySelector(fallbackSelector) : null)) as HTMLElement | null;
}

function getScrollableParent(element: HTMLElement): HTMLElement | null {
  let parent = element.parentElement;
  while (parent) {
    const style = window.getComputedStyle(parent);
    const canScroll = /(auto|scroll|overlay)/.test(style.overflowY);
    if (canScroll && parent.scrollHeight > parent.clientHeight + 4) return parent;
    parent = parent.parentElement;
  }
  return null;
}

function getDesiredTargetTop(rawRect: TourRect, step: TourStep, visibleTop: number, visibleBottom: number, panelHeightOverride?: number | null): number {
  const visibleHeight = Math.max(160, visibleBottom - visibleTop);
  const targetHeight = Math.min(rawRect.height, visibleHeight - 24);
  const panelHeight = panelHeightOverride || getEstimatedPanelHeight(step);
  const placement = step.placement || 'below';

  if (placement === 'below' || placement === 'bottom-left' || placement === 'bottom-right') {
    const topForPanelBelow = visibleBottom - panelHeight - TOUR_PANEL_GAP - TOUR_SPOTLIGHT_PADDING - targetHeight - 10;
    return clamp(topForPanelBelow, visibleTop + 12, visibleBottom - targetHeight - 12);
  }

  if (placement === 'above' || placement === 'top-left' || placement === 'top-right') {
    const topForPanelAbove = visibleTop + panelHeight + TOUR_PANEL_GAP + TOUR_SPOTLIGHT_PADDING + 10;
    return clamp(topForPanelAbove, visibleTop + 12, visibleBottom - targetHeight - 12);
  }

  return clamp(visibleTop + (visibleHeight - targetHeight) / 2, visibleTop + 12, visibleBottom - targetHeight - 12);
}

function nudgeElementIntoSafeViewport(element: HTMLElement, step: TourStep, panelHeightOverride?: number | null) {
  const scrollParent = getScrollableParent(element);
  element.scrollIntoView({ behavior: 'auto', block: step.scrollBlock || 'center', inline: 'nearest' });

  const adjust = () => {
    const rawRect = getRawTargetRect(step.selector, step.fallbackSelector);
    if (!rawRect) return;

    const safe = getSafeBounds();
    const parentRect = scrollParent?.getBoundingClientRect();
    const visibleTop = Math.max(safe.top, parentRect ? parentRect.top + 16 : safe.top);
    const visibleBottom = Math.min(safe.bottom, parentRect ? parentRect.bottom - 16 : safe.bottom);
    const desiredTop = getDesiredTargetTop(rawRect, step, visibleTop, visibleBottom, panelHeightOverride);
    const delta = rawRect.top - desiredTop;

    if (Math.abs(delta) < 2) return;
    if (scrollParent) {
      scrollParent.scrollBy({ top: delta, behavior: 'auto' });
    } else {
      window.scrollBy({ top: delta, behavior: 'auto' });
    }
  };

  window.requestAnimationFrame(() => {
    adjust();
    window.requestAnimationFrame(adjust);
  });
}

function renderBullets(items?: string[]): ReactNode {
  if (!items?.length) return null;
  return (
    <ul className="mt-3 space-y-2 rounded-xl border border-border/60 bg-secondary/20 p-3 text-xs leading-5 text-muted-foreground">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/80" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function dispatchTourAction(action: TourAction) {
  if (action === 'open-nextcloud-import') {
    window.dispatchEvent(new CustomEvent('workbench-tour:open-nextcloud-import'));
    return;
  }
  if (action === 'focus-nextcloud-root') {
    window.dispatchEvent(new CustomEvent('workbench-tour:focus-nextcloud-folder', { detail: { kind: 'root' } }));
    return;
  }
  if (action === 'focus-nextcloud-synthetic') {
    window.dispatchEvent(new CustomEvent('workbench-tour:focus-nextcloud-folder', { detail: { kind: 'synthetic' } }));
    return;
  }
  if (action === 'select-nextcloud-starter-set') {
    window.dispatchEvent(new CustomEvent('workbench-tour:select-nextcloud-starter-set'));
    return;
  }
  if (action === 'open-action-plan-board') {
    window.dispatchEvent(new CustomEvent('workbench-tour:open-action-plan-board'));
    return;
  }
  if (action === 'open-candidate-internals') {
    window.dispatchEvent(new CustomEvent('workbench-tour:open-candidate-internals'));
  }
}

export default function GuidedWorkbenchTour() {
  const location = useLocation();
  const navigate = useNavigate();
  const tourParam = new URLSearchParams(location.search).get('tour');
  const activeTourKind: ActiveTourKind | null = tourParam === '1'
    ? 'document-library'
    : tourParam && tourParam in TOUR_STEPS_BY_KIND
      ? (tourParam as ActiveTourKind)
      : null;
  const isActive = Boolean(activeTourKind);
  const activeTourSteps = activeTourKind ? TOUR_STEPS_BY_KIND[activeTourKind] : DOCUMENT_LIBRARY_TOUR_STEPS;
  const activeTourSearch = activeTourKind ? TOUR_SEARCH_BY_KIND[activeTourKind] : '?tour=1';
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<TourRect | null>(null);
  const [panelReady, setPanelReady] = useState(false);
  const [measuredPanelHeight, setMeasuredPanelHeight] = useState<number | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const measuredPanelHeightRef = useRef<number | null>(null);
  const previousTourKindRef = useRef<ActiveTourKind | null>(activeTourKind);
  const step = activeTourSteps[stepIndex] ?? activeTourSteps[0];
  const progress = useMemo(() => Math.round(((stepIndex + 1) / activeTourSteps.length) * 100), [activeTourSteps.length, stepIndex]);

  const closeTour = useCallback(() => {
    const params = new URLSearchParams(location.search);
    params.delete('tour');
    const search = params.toString();
    navigate({ pathname: location.pathname, search: search ? `?${search}` : '' }, { replace: true });
  }, [location.pathname, location.search, navigate]);

  const completeDocumentLibraryTour = useCallback(() => {
    try {
      window.localStorage.setItem(TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:nextcloud-scroll-top'));
    window.dispatchEvent(new CustomEvent('workbench-tour:document-library-complete'));
    closeTour();
  }, [closeTour]);

  const completeWorkflowTour = useCallback(() => {
    try {
      window.localStorage.setItem(WORKFLOW_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:workflow-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-document-review-tour'));
    closeTour();
  }, [closeTour]);

  const completeDocumentReviewTour = useCallback(() => {
    try {
      window.localStorage.setItem(DOCUMENT_REVIEW_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:document-review-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-policy-comparison-tour'));
    closeTour();
  }, [closeTour]);

  const completePolicyComparisonTour = useCallback(() => {
    try {
      window.localStorage.setItem(POLICY_COMPARISON_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:policy-comparison-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-action-plan-tour'));
    closeTour();
  }, [closeTour]);

  const completeActionPlanTour = useCallback(() => {
    try {
      window.localStorage.setItem(ACTION_PLAN_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:action-plan-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-candidate-review-tour'));
    closeTour();
  }, [closeTour]);

  const completeCandidateReviewTour = useCallback(() => {
    try {
      window.localStorage.setItem(CANDIDATE_REVIEW_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:candidate-review-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-deck-center-tour'));
    closeTour();
  }, [closeTour]);

  const completeDeckCenterTour = useCallback(() => {
    try {
      window.localStorage.setItem(DECK_CENTER_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:deck-center-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-run-history-tour'));
    closeTour();
  }, [closeTour]);

  const completeRunHistoryTour = useCallback(() => {
    try {
      window.localStorage.setItem(RUN_HISTORY_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:run-history-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-runtime-controls-tour'));
    closeTour();
  }, [closeTour]);

  const completeRuntimeControlsTour = useCallback(() => {
    try {
      window.localStorage.setItem(RUNTIME_CONTROLS_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:runtime-controls-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-preferences-tour'));
    closeTour();
  }, [closeTour]);

  const completePreferencesTour = useCallback(() => {
    try {
      window.localStorage.setItem(PREFERENCES_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:preferences-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-overview-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabOverviewTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_OVERVIEW_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-overview-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-runtime-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabRuntimeTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_RUNTIME_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-runtime-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-document-experiments-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabDocumentExperimentsTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_DOCUMENT_EXPERIMENTS_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-document-experiments-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-workflow-inspector-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabWorkflowInspectorTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_WORKFLOW_INSPECTOR_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-workflow-inspector-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-benchmarks-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabBenchmarksTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_BENCHMARKS_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-benchmarks-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-evals-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabEvalsTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_EVALS_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-evals-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-artifacts-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabArtifactsTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_ARTIFACTS_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-artifacts-complete'));
    window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-lab-evidenceops-tour'));
    closeTour();
  }, [closeTour]);

  const completeLabEvidenceOpsTour = useCallback(() => {
    try {
      window.localStorage.setItem(LAB_EVIDENCEOPS_TOUR_COMPLETED_STORAGE_KEY, '1');
    } catch {
      // Ignore private browsing / storage failures; the route still closes cleanly.
    }
    window.dispatchEvent(new CustomEvent('workbench-tour:lab-evidenceops-complete'));
    closeTour();
  }, [closeTour]);

  const completeActiveTour = useCallback(() => {
    if (activeTourKind === 'document-library') {
      completeDocumentLibraryTour();
      return;
    }
    if (activeTourKind === 'workflow') {
      completeWorkflowTour();
      return;
    }
    if (activeTourKind === 'document-review') {
      completeDocumentReviewTour();
      return;
    }
    if (activeTourKind === 'policy-comparison') {
      completePolicyComparisonTour();
      return;
    }
    if (activeTourKind === 'action-plan') {
      completeActionPlanTour();
      return;
    }
    if (activeTourKind === 'candidate-review') {
      completeCandidateReviewTour();
      return;
    }
    if (activeTourKind === 'deck-center') {
      completeDeckCenterTour();
      return;
    }
    if (activeTourKind === 'run-history') {
      completeRunHistoryTour();
      return;
    }
    if (activeTourKind === 'runtime-controls') {
      completeRuntimeControlsTour();
      return;
    }
    if (activeTourKind === 'preferences') {
      completePreferencesTour();
      return;
    }
    if (activeTourKind === 'lab-overview') {
      completeLabOverviewTour();
      return;
    }
    if (activeTourKind === 'lab-runtime') {
      completeLabRuntimeTour();
      return;
    }
    if (activeTourKind === 'lab-document-experiments') {
      completeLabDocumentExperimentsTour();
      return;
    }
    if (activeTourKind === 'lab-workflow-inspector') {
      completeLabWorkflowInspectorTour();
      return;
    }
    if (activeTourKind === 'lab-benchmarks') {
      completeLabBenchmarksTour();
      return;
    }
    if (activeTourKind === 'lab-evals') {
      completeLabEvalsTour();
      return;
    }
    if (activeTourKind === 'lab-artifacts') {
      completeLabArtifactsTour();
      return;
    }
    if (activeTourKind === 'lab-evidenceops') {
      completeLabEvidenceOpsTour();
      return;
    }
    closeTour();
  }, [activeTourKind, closeTour, completeDocumentLibraryTour, completeWorkflowTour, completeDocumentReviewTour, completePolicyComparisonTour, completeActionPlanTour, completeCandidateReviewTour, completeDeckCenterTour, completeRunHistoryTour, completeRuntimeControlsTour, completePreferencesTour, completeLabOverviewTour, completeLabRuntimeTour, completeLabDocumentExperimentsTour, completeLabWorkflowInspectorTour, completeLabBenchmarksTour, completeLabEvalsTour, completeLabArtifactsTour, completeLabEvidenceOpsTour]);

  const goToStep = useCallback((nextIndex: number) => {
    if (nextIndex < 0) return;
    if (nextIndex >= activeTourSteps.length) return completeActiveTour();
    const nextStep = activeTourSteps[nextIndex];
    setPanelReady(false);
    measuredPanelHeightRef.current = null;
    setMeasuredPanelHeight(null);
    setTargetRect(null);
    setStepIndex(nextIndex);
    if (location.pathname !== nextStep.path || `?${new URLSearchParams(location.search).toString()}` !== activeTourSearch) {
      navigate({ pathname: nextStep.path, search: activeTourSearch }, { replace: true });
    }
  }, [activeTourKind, activeTourSearch, activeTourSteps, completeActiveTour, location.pathname, location.search, navigate]);

  const measureStep = useCallback((scrollIntoView = false, revealPanel = true) => {
    if (!isActive || !step) return;
    const element = getScrollTarget(step.selector, step.fallbackSelector);
    if (element && scrollIntoView) {
      nudgeElementIntoSafeViewport(element, step, measuredPanelHeightRef.current);
    }
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        const rect = getTargetRect(step.selector, step.fallbackSelector, step);
        setTargetRect(rect);
        if (revealPanel) setPanelReady(true);
      });
    });
  }, [isActive, step]);

  useEffect(() => {
    if (previousTourKindRef.current === activeTourKind) return;
    previousTourKindRef.current = activeTourKind;
    setStepIndex(0);
    setPanelReady(false);
    measuredPanelHeightRef.current = null;
    setMeasuredPanelHeight(null);
    setTargetRect(null);
  }, [activeTourKind]);

  useEffect(() => {
    if (!isActive) return;
    setPanelReady(false);
    measuredPanelHeightRef.current = null;
    setMeasuredPanelHeight(null);
    setTargetRect(null);
    if (location.pathname !== step.path) {
      navigate({ pathname: step.path, search: activeTourSearch }, { replace: true });
      return;
    }

    const actionTimers = (step.actions || []).map((action, index) => (
      window.setTimeout(() => dispatchTourAction(action), action === 'open-nextcloud-import' ? 20 : 160 + index * 80)
    ));
    const hasSheetAction = step.actions?.includes('open-nextcloud-import');
    const firstMeasureDelay = hasSheetAction ? 620 : 180;
    const settleMeasureDelay = hasSheetAction ? 860 : 360;
    const timers = [
      window.setTimeout(() => measureStep(true, false), firstMeasureDelay),
      window.setTimeout(() => measureStep(true, true), settleMeasureDelay),
    ];
    return () => [...actionTimers, ...timers].forEach((timer) => window.clearTimeout(timer));
  }, [activeTourSearch, isActive, location.pathname, measureStep, navigate, step]);

  useEffect(() => {
    if (!isActive) return;
    const handleResizeOrScroll = () => measureStep(false);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeTour();
      if (event.key === 'ArrowRight') goToStep(stepIndex + 1);
      if (event.key === 'ArrowLeft') goToStep(stepIndex - 1);
    };
    window.addEventListener('resize', handleResizeOrScroll);
    window.addEventListener('scroll', handleResizeOrScroll, true);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('resize', handleResizeOrScroll);
      window.removeEventListener('scroll', handleResizeOrScroll, true);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [closeTour, goToStep, isActive, measureStep, stepIndex]);


  useEffect(() => {
    if (!panelReady) return;
    const panel = panelRef.current;
    if (!panel) return;
    const frame = window.requestAnimationFrame(() => {
      const nextHeight = panel.getBoundingClientRect().height;
      measuredPanelHeightRef.current = nextHeight;
      setMeasuredPanelHeight(nextHeight);
      const element = getScrollTarget(step.selector, step.fallbackSelector);
      if (!element) return;
      window.setTimeout(() => {
        nudgeElementIntoSafeViewport(element, step, nextHeight);
        window.requestAnimationFrame(() => {
          const rect = getTargetRect(step.selector, step.fallbackSelector, step);
          setTargetRect(rect);
        });
      }, 20);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [panelReady, stepIndex, step]);

  if (!isActive) return null;
  const panelStyle = getPanelStyle(targetRect, step, measuredPanelHeight);
  const panelIsCompact = Boolean(step.compactPanel);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[80] pointer-events-none">
        {targetRect ? (
          <motion.div
            key={`spotlight-${step.id}`}
            className="absolute rounded-2xl border border-primary/75 bg-transparent shadow-[0_0_0_9999px_rgba(0,0,0,0.72),0_0_44px_-12px_hsl(var(--primary))]"
            style={{ top: targetRect.top - TOUR_SPOTLIGHT_PADDING, left: targetRect.left - TOUR_SPOTLIGHT_PADDING, width: targetRect.width + TOUR_SPOTLIGHT_PADDING * 2, height: targetRect.height + TOUR_SPOTLIGHT_PADDING * 2 }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.14, ease: [0.16, 1, 0.3, 1] }}
          />
        ) : (
          <motion.div className="absolute inset-0 bg-background/70" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
        )}
        {panelReady ? (
          <motion.div
            ref={panelRef}
            key={`panel-${step.id}`}
            className={cn(
              'pointer-events-auto fixed max-h-[calc(100vh-32px)] overflow-y-auto rounded-2xl border border-border/70 bg-card/95 text-card-foreground shadow-2xl shadow-black/30 backdrop-blur-xl',
              panelIsCompact ? 'p-3' : 'p-4',
            )}
            style={panelStyle}
            initial={{ opacity: 0, scale: 0.992 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.992 }}
            transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className={cn("flex items-center justify-between gap-3", panelIsCompact ? "mb-2" : "mb-3")}>
              <div className="flex min-w-0 items-center gap-2">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
                  {stepIndex === activeTourSteps.length - 1 ? <CheckCircle2 className="h-4 w-4" /> : <Compass className="h-4 w-4" />}
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-primary/75">{step.eyebrow}</p>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-secondary">
                    <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              </div>
              <button type="button" onClick={closeTour} className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground" aria-label="Close guided tour"><X className="h-4 w-4" /></button>
            </div>
            <h3 className="text-base font-semibold leading-snug text-foreground">{step.title}</h3>
            <p className={cn("text-sm text-muted-foreground", panelIsCompact ? "mt-1.5 leading-5" : "mt-2 leading-6")}>{step.body}</p>
            {renderBullets(step.bullets)}
            {step.cta ? (
              <Button
                variant="outline"
                size="sm"
                className="mt-3 h-8 w-full justify-center text-xs"
                onClick={() => {
                  dispatchTourAction(step.cta!.action);
                  window.setTimeout(() => measureStep(false), 180);
                }}
              >
                <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" /> {step.cta.label}
              </Button>
            ) : null}
            {step.link ? (
              <a
                href={step.link.href}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex w-full items-center justify-center rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs font-medium text-primary transition-colors hover:bg-primary/10"
              >
                {step.link.label} <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
              </a>
            ) : null}
            {step.tip ? <div className={cn("rounded-xl border border-primary/15 bg-primary/5 text-xs leading-5 text-muted-foreground", panelIsCompact ? "mt-2 p-2.5" : "mt-3 p-3")}><div className="mb-1 flex items-center gap-2 text-primary/90"><Sparkles className="h-3.5 w-3.5" /><span className="font-medium">Tip</span></div>{step.tip}</div> : null}
            <div className={cn("flex items-center justify-between gap-3", panelIsCompact ? "mt-3" : "mt-4")}>
              <div className="text-[10px] text-muted-foreground">{stepIndex + 1} of {activeTourSteps.length}</div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className={cn('h-8 px-3 text-xs', stepIndex === 0 && 'invisible')} onClick={() => goToStep(stepIndex - 1)}><ArrowLeft className="mr-1 h-3.5 w-3.5" /> Back</Button>
                <Button size="sm" className="h-8 px-3 text-xs" onClick={() => goToStep(stepIndex + 1)}>{stepIndex === activeTourSteps.length - 1 ? 'Finish here' : 'Next'}{stepIndex === activeTourSteps.length - 1 ? null : <ArrowRight className="ml-1 h-3.5 w-3.5" />}</Button>
              </div>
            </div>
          </motion.div>
        ) : null}
      </div>
    </AnimatePresence>
  );
}

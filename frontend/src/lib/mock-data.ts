// ─── Documents ─────────────────────────────────────────────
export interface Document {
  id: string; name: string; type: string; status: 'indexed' | 'indexing' | 'error' | 'pending';
  size: string; chunks: number; chars: number; loaderStrategy: string; indexedAt: string; warnings?: string[];
}

export const documents: Document[] = [
  { id: 'd1', name: 'Master Service Agreement v4.2', type: 'PDF', status: 'indexed', size: '2.4 MB', chunks: 347, chars: 189420, loaderStrategy: 'pdf_plumber', indexedAt: '2024-03-14T09:23:00Z' },
  { id: 'd2', name: 'Data Processing Addendum 2024', type: 'PDF', status: 'indexed', size: '890 KB', chunks: 124, chars: 67200, loaderStrategy: 'pdf_plumber', indexedAt: '2024-03-14T09:25:00Z' },
  { id: 'd3', name: 'Information Security Policy v3.1', type: 'DOCX', status: 'indexed', size: '1.1 MB', chunks: 198, chars: 102300, loaderStrategy: 'docx_loader', indexedAt: '2024-03-13T14:10:00Z' },
  { id: 'd4', name: 'Cloud Infrastructure SLA', type: 'PDF', status: 'indexed', size: '456 KB', chunks: 89, chars: 43100, loaderStrategy: 'pdf_plumber', indexedAt: '2024-03-13T14:12:00Z' },
  { id: 'd5', name: 'GDPR Compliance Checklist', type: 'PDF', status: 'indexing', size: '320 KB', chunks: 0, chars: 0, loaderStrategy: 'pdf_plumber', indexedAt: '' },
  { id: 'd6', name: 'Vendor Risk Assessment Template', type: 'XLSX', status: 'indexed', size: '780 KB', chunks: 56, chars: 28900, loaderStrategy: 'spreadsheet_loader', indexedAt: '2024-03-12T11:00:00Z' },
  { id: 'd7', name: 'Employee Handbook 2024', type: 'PDF', status: 'indexed', size: '3.2 MB', chunks: 512, chars: 267800, loaderStrategy: 'pdf_plumber', indexedAt: '2024-03-11T16:30:00Z' },
  { id: 'd8', name: 'Technical Architecture Brief', type: 'PDF', status: 'error', size: '5.1 MB', chunks: 0, chars: 0, loaderStrategy: 'pdf_plumber', indexedAt: '', warnings: ['OCR fallback failed on pages 12-15'] },
  { id: 'd9', name: 'Sarah Chen - Senior ML Engineer CV', type: 'PDF', status: 'indexed', size: '245 KB', chunks: 34, chars: 18200, loaderStrategy: 'pdf_plumber', indexedAt: '2024-03-15T08:00:00Z' },
  { id: 'd10', name: 'Q1 2024 Board Memo', type: 'PDF', status: 'pending', size: '1.8 MB', chunks: 0, chars: 0, loaderStrategy: 'pdf_plumber', indexedAt: '' },
];

// ─── Workflow Runs ─────────────────────────────────────────
export interface WorkflowRun {
  id: string; workflow: string; status: 'completed' | 'running' | 'warning' | 'error';
  documents: string[]; startedAt: string; duration: string; findings?: number; artifacts?: string[];
}

export const workflowRuns: WorkflowRun[] = [
  { id: 'r1', workflow: 'Document Review', status: 'completed', documents: ['Master Service Agreement v4.2'], startedAt: '2024-03-15T10:30:00Z', duration: '2m 14s', findings: 12, artifacts: ['review_deck.pptx', 'review.json'] },
  { id: 'r2', workflow: 'Policy Comparison', status: 'completed', documents: ['Info Security Policy v3.1', 'GDPR Checklist'], startedAt: '2024-03-15T09:15:00Z', duration: '3m 42s', findings: 8, artifacts: ['comparison_deck.pptx', 'diff.json'] },
  { id: 'r3', workflow: 'Candidate Review', status: 'completed', documents: ['Sarah Chen CV'], startedAt: '2024-03-15T08:45:00Z', duration: '1m 08s', findings: 6, artifacts: ['candidate_deck.pptx'] },
  { id: 'r4', workflow: 'Action Plan', status: 'warning', documents: ['Vendor Risk Assessment'], startedAt: '2024-03-14T16:20:00Z', duration: '4m 31s', findings: 15, artifacts: ['action_plan.pptx'] },
  { id: 'r5', workflow: 'Document Review', status: 'error', documents: ['Technical Architecture Brief'], startedAt: '2024-03-14T15:00:00Z', duration: '0m 23s' },
  { id: 'r6', workflow: 'Policy Comparison', status: 'running', documents: ['MSA v4.2', 'Cloud SLA'], startedAt: '2024-03-15T11:00:00Z', duration: '—' },
];

// ─── Findings ──────────────────────────────────────────────
export interface Finding {
  id: string; title: string; severity: 'critical' | 'high' | 'medium' | 'low'; category: string;
  description: string; source: string; chunkId: string; confidence: number; recommendation: string;
}

export const findings: Finding[] = [
  { id: 'f1', title: 'Unlimited liability clause in Section 7.3', severity: 'critical', category: 'Legal Risk', description: 'The MSA contains an unlimited liability provision that exposes the organization to uncapped financial risk in case of breach.', source: 'Master Service Agreement v4.2', chunkId: 'chunk_142', confidence: 0.94, recommendation: 'Negotiate liability cap at 2x annual contract value' },
  { id: 'f2', title: 'Missing data residency requirements', severity: 'high', category: 'Compliance', description: 'No explicit data residency clause found. GDPR Article 44-49 requires clear specification of data transfer mechanisms.', source: 'Data Processing Addendum 2024', chunkId: 'chunk_067', confidence: 0.91, recommendation: 'Add Standard Contractual Clauses (SCCs) appendix' },
  { id: 'f3', title: 'SLA uptime target below industry standard', severity: 'medium', category: 'Operational Risk', description: 'Current SLA specifies 99.5% uptime. Industry standard for enterprise cloud services is 99.95%.', source: 'Cloud Infrastructure SLA', chunkId: 'chunk_023', confidence: 0.88, recommendation: 'Renegotiate to 99.95% with defined penalty structure' },
  { id: 'f4', title: 'Auto-renewal with 90-day notice period', severity: 'medium', category: 'Commercial', description: 'Contract auto-renews with a 90-day notice requirement, creating risk of unintended renewal.', source: 'Master Service Agreement v4.2', chunkId: 'chunk_289', confidence: 0.92, recommendation: 'Reduce notice period to 30 days or add calendar reminder system' },
  { id: 'f5', title: 'Weak incident response timeframes', severity: 'high', category: 'Security', description: 'Security incident notification timeline is "reasonable effort" without specific hour commitment.', source: 'Information Security Policy v3.1', chunkId: 'chunk_156', confidence: 0.89, recommendation: 'Define explicit 24-hour notification requirement for critical incidents' },
];

// ─── Candidate ─────────────────────────────────────────────
export const candidateData = {
  name: 'Sarah Chen',
  title: 'Senior ML Engineer',
  location: 'San Francisco, CA',
  experience: '8 years',
  education: 'M.S. Computer Science, Stanford University',
  overallScore: 87,
  recommendation: 'Strong Hire',
  strengths: [
    'Deep expertise in transformer architectures and LLM fine-tuning',
    'Production ML systems experience at scale (10M+ daily predictions)',
    'Strong publication record (3 NeurIPS, 2 ICML papers)',
    'Led team of 5 ML engineers at Series B startup',
    'Hands-on with MLOps: Kubeflow, MLflow, Weights & Biases',
  ],
  gaps: [
    'Limited experience with on-premise/edge deployment',
    'No direct experience with regulatory compliance (HIPAA, SOC2)',
    'Management experience limited to IC lead roles',
  ],
  experiences: [
    { company: 'Anthropic', role: 'Senior ML Engineer', period: '2022 — Present', highlights: ['RLHF pipeline optimization', 'Constitutional AI research', 'Reduced training costs by 34%'] },
    { company: 'Scale AI', role: 'ML Engineer', period: '2020 — 2022', highlights: ['Built data quality scoring system', 'Annotation pipeline automation', 'Cross-functional product collaboration'] },
    { company: 'Google Brain', role: 'Research Engineer', period: '2018 — 2020', highlights: ['Contributed to T5 model development', 'Published 2 papers on attention mechanisms', 'Mentored 3 interns'] },
  ],
  senioritySignals: ['Architectural decision-making ownership', 'Cross-team technical influence', 'Mentorship track record', 'Production system ownership'],
};

// ─── Models / Providers ────────────────────────────────────
export interface ModelConfig {
  id: string; provider: string; model: string; family: string; quantization: string;
  latency: number; outputChars: number; adherence: number; groundedness: number;
  useCaseFit: number; runtimeBucket: string;
}

export const models: ModelConfig[] = [
  { id: 'm1', provider: 'ollama', model: 'llama3.1:70b-instruct-q4_K_M', family: 'Llama 3.1', quantization: 'Q4_K_M', latency: 12.4, outputChars: 3420, adherence: 0.89, groundedness: 0.87, useCaseFit: 0.85, runtimeBucket: 'local_gpu' },
  { id: 'm2', provider: 'ollama', model: 'qwen2.5:32b-instruct-q5_K_M', family: 'Qwen 2.5', quantization: 'Q5_K_M', latency: 8.7, outputChars: 2980, adherence: 0.92, groundedness: 0.90, useCaseFit: 0.88, runtimeBucket: 'local_gpu' },
  { id: 'm3', provider: 'openai-compatible', model: 'gpt-4o', family: 'GPT-4', quantization: 'N/A', latency: 3.2, outputChars: 4100, adherence: 0.96, groundedness: 0.93, useCaseFit: 0.94, runtimeBucket: 'cloud_api' },
  { id: 'm4', provider: 'ollama', model: 'mistral:7b-instruct-v0.3', family: 'Mistral', quantization: 'Q4_0', latency: 2.1, outputChars: 1890, adherence: 0.78, groundedness: 0.72, useCaseFit: 0.70, runtimeBucket: 'local_gpu' },
  { id: 'm5', provider: 'huggingface_server', model: 'microsoft/phi-3-medium-128k', family: 'Phi-3', quantization: 'FP16', latency: 6.8, outputChars: 2670, adherence: 0.85, groundedness: 0.82, useCaseFit: 0.80, runtimeBucket: 'local_gpu' },
];

// ─── Artifacts ─────────────────────────────────────────────
export interface Artifact {
  id: string; name: string; type: 'pptx' | 'json' | 'pdf'; workflow: string;
  createdAt: string; size: string; status: 'ready' | 'generating' | 'error';
}

export const artifacts: Artifact[] = [
  { id: 'a1', name: 'MSA Risk Review Deck', type: 'pptx', workflow: 'Document Review', createdAt: '2024-03-15T10:35:00Z', size: '2.1 MB', status: 'ready' },
  { id: 'a2', name: 'Policy Comparison Summary', type: 'pptx', workflow: 'Policy Comparison', createdAt: '2024-03-15T09:20:00Z', size: '1.8 MB', status: 'ready' },
  { id: 'a3', name: 'Sarah Chen — Candidate Review', type: 'pptx', workflow: 'Candidate Review', createdAt: '2024-03-15T08:50:00Z', size: '1.2 MB', status: 'ready' },
  { id: 'a4', name: 'Vendor Risk Action Plan', type: 'pptx', workflow: 'Action Plan', createdAt: '2024-03-14T16:30:00Z', size: '1.5 MB', status: 'ready' },
  { id: 'a5', name: 'contract_payload.json', type: 'json', workflow: 'Document Review', createdAt: '2024-03-15T10:34:00Z', size: '48 KB', status: 'ready' },
  { id: 'a6', name: 'SLA vs MSA Comparison', type: 'pptx', workflow: 'Policy Comparison', createdAt: '2024-03-15T11:05:00Z', size: '—', status: 'generating' },
];

// ─── MCP Tools ─────────────────────────────────────────────
export const mcpTools = [
  { name: 'list_open_actions', description: 'List all open action items across repositories', status: 'active', lastCall: '2024-03-15T10:45:00Z' },
  { name: 'search_documents', description: 'Search indexed documents by semantic query', status: 'active', lastCall: '2024-03-15T10:30:00Z' },
  { name: 'get_repository_summary', description: 'Get summary stats for a document repository', status: 'active', lastCall: '2024-03-15T09:00:00Z' },
  { name: 'update_action_status', description: 'Update status of an action item', status: 'active', lastCall: '2024-03-14T16:45:00Z' },
  { name: 'detect_repository_drift', description: 'Check for changes since last sync', status: 'degraded', lastCall: '2024-03-14T12:00:00Z' },
  { name: 'register_external_sync', description: 'Register external system sync plan', status: 'inactive', lastCall: '' },
];

// ─── Chat Messages ─────────────────────────────────────────
export const chatMessages = [
  { id: 'c1', role: 'user' as const, content: 'What are the key liability provisions in the Master Service Agreement?', timestamp: '2024-03-15T10:00:00Z' },
  { id: 'c2', role: 'assistant' as const, content: 'Based on the Master Service Agreement v4.2, I identified three key liability provisions:\n\n**1. Unlimited Liability (Section 7.3)**\nThe agreement contains an unlimited liability clause that exposes both parties to uncapped financial risk. This is unusual for enterprise SaaS agreements.\n\n**2. Indemnification Scope (Section 7.5)**\nIndemnification covers IP infringement and data breaches, but notably excludes consequential damages.\n\n**3. Limitation Period (Section 7.8)**\nClaims must be brought within 12 months of the event, which is shorter than the typical 24-month window.', timestamp: '2024-03-15T10:00:05Z', sources: [{ doc: 'MSA v4.2', chunk: 'chunk_142', score: 0.94 }, { doc: 'MSA v4.2', chunk: 'chunk_156', score: 0.91 }] },
  { id: 'c3', role: 'user' as const, content: 'How does this compare to industry standard terms?', timestamp: '2024-03-15T10:01:00Z' },
  { id: 'c4', role: 'assistant' as const, content: 'Compared to industry standards, several provisions deviate significantly:\n\n• **Liability cap**: Standard practice is 1-2x annual contract value. The unlimited clause here is a red flag.\n• **Notice period**: 90-day auto-renewal notice is aggressive; 30-60 days is typical.\n• **SLA target**: 99.5% is below the 99.95% enterprise standard.\n\nI recommend prioritizing the liability cap negotiation before proceeding.', timestamp: '2024-03-15T10:01:08Z', sources: [{ doc: 'MSA v4.2', chunk: 'chunk_289', score: 0.92 }, { doc: 'Cloud SLA', chunk: 'chunk_023', score: 0.88 }] },
];

// ─── Action Items ──────────────────────────────────────────
export interface ActionItem {
  id: string; title: string; owner: string; dueDate: string; priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'in_progress' | 'blocked' | 'done'; evidence: string; source: string;
}

export const actionItems: ActionItem[] = [
  { id: 'ai1', title: 'Negotiate liability cap with vendor legal', owner: 'Maria Santos', dueDate: '2024-03-22', priority: 'critical', status: 'in_progress', evidence: 'Section 7.3 unlimited liability clause', source: 'MSA v4.2' },
  { id: 'ai2', title: 'Draft SCCs appendix for data residency', owner: 'James Park', dueDate: '2024-03-25', priority: 'high', status: 'open', evidence: 'Missing data residency clause in DPA', source: 'DPA 2024' },
  { id: 'ai3', title: 'Request revised SLA with 99.95% target', owner: 'Maria Santos', dueDate: '2024-03-20', priority: 'high', status: 'done', evidence: 'Current SLA at 99.5%', source: 'Cloud SLA' },
  { id: 'ai4', title: 'Define incident response SLOs', owner: 'Alex Rivera', dueDate: '2024-03-28', priority: 'high', status: 'open', evidence: 'Vague "reasonable effort" language', source: 'InfoSec Policy v3.1' },
  { id: 'ai5', title: 'Set up auto-renewal calendar alerts', owner: 'Operations', dueDate: '2024-03-18', priority: 'medium', status: 'in_progress', evidence: '90-day notice period risk', source: 'MSA v4.2' },
  { id: 'ai6', title: 'Review vendor SOC2 Type II report', owner: 'Alex Rivera', dueDate: '2024-04-01', priority: 'medium', status: 'blocked', evidence: 'Awaiting vendor response', source: 'Vendor Risk Assessment' },
];

// ─── Comparison Data ───────────────────────────────────────
export interface ComparisonDiff {
  id: string; clause: string; docA: string; docB: string; impact: 'breaking' | 'significant' | 'minor';
  category: string; businessImpact: string;
}

export const comparisonDiffs: ComparisonDiff[] = [
  { id: 'cd1', clause: 'Liability Cap', docA: 'Unlimited liability for both parties', docB: 'Liability capped at 2x annual contract value', impact: 'breaking', category: 'Legal', businessImpact: 'Uncapped financial exposure in MSA vs. protected position in revised terms' },
  { id: 'cd2', clause: 'Data Residency', docA: 'No specification', docB: 'EU-only data processing with SCCs for transfers', impact: 'significant', category: 'Compliance', businessImpact: 'GDPR non-compliance risk without explicit residency terms' },
  { id: 'cd3', clause: 'Termination Notice', docA: '90 days prior to renewal', docB: '30 days prior to renewal', impact: 'significant', category: 'Commercial', businessImpact: 'Reduced lock-in risk with shorter notice period' },
  { id: 'cd4', clause: 'SLA Uptime', docA: '99.5% monthly', docB: '99.95% monthly with credits', impact: 'significant', category: 'Operational', businessImpact: 'Improved service reliability guarantees and financial remedies' },
  { id: 'cd5', clause: 'IP Ownership', docA: 'Joint ownership of derivatives', docB: 'Client retains all derivative IP', impact: 'breaking', category: 'Legal', businessImpact: 'Critical difference in intellectual property rights allocation' },
];

// ─── Structured Output Tasks ───────────────────────────────
export const structuredTasks = [
  { id: 'st1', name: 'extraction', label: 'Entity Extraction', description: 'Extract structured entities from documents', icon: 'Layers' },
  { id: 'st2', name: 'summary', label: 'Document Summary', description: 'Generate executive summaries with key points', icon: 'FileText' },
  { id: 'st3', name: 'checklist', label: 'Compliance Checklist', description: 'Evaluate documents against compliance criteria', icon: 'CheckSquare' },
  { id: 'st4', name: 'document_agent', label: 'Document Agent', description: 'Multi-step document analysis with reasoning', icon: 'Bot' },
  { id: 'st5', name: 'cv_analysis', label: 'CV Analysis', description: 'Parse and evaluate candidate profiles', icon: 'User' },
  { id: 'st6', name: 'code_analysis', label: 'Code Analysis', description: 'Analyze code structure and quality', icon: 'Code' },
];

// ─── System Stats ──────────────────────────────────────────
export const systemStats = {
  totalDocuments: 10,
  totalChunks: 1360,
  totalChars: 717920,
  indexedDocuments: 7,
  activeWorkflows: 1,
  completedRuns: 14,
  artifactsGenerated: 23,
  avgLatency: '6.2s',
  embeddingModel: 'nomic-embed-text',
  generationModel: 'qwen2.5:32b-instruct',
  provider: 'ollama',
};

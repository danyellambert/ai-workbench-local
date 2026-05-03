import type {
  ProviderConnection,
  RuntimeProfile,
  ConnectionPolicyRule,
  OperatorPreferences,
} from '@/types/settings';

export const PROVIDER_CONNECTIONS: ProviderConnection[] = [
  {
    id: 'ollama-local',
    name: 'Ollama Local',
    providerFamily: 'ollama',
    mode: 'local',
    baseUrl: 'http://localhost:11434',
    authMethod: 'none',
    apiKeyConfigured: false,
    status: 'connected',
    preferredModel: 'nemotron-3-super:cloud',
    lastChecked: '2 min ago',
    description: 'Local Ollama daemon on GPU workstation. No API key required and suited to primary day-to-day execution.',
    capabilities: { generation: true, embeddings: true, reranking: false, structuredOutputs: true, vision: false, toolCalling: false, streaming: true },
    role: 'production',
    workflowFit: ['document-review', 'comparison', 'action-plan', 'candidate-review', 'chat-experiments', 'workflow-inspector'],
    usageNote: 'Primary production connection. Supports all core workflows with local GPU inference.',
  },
  {
    id: 'ollama-hosted',
    name: 'Ollama Hosted',
    providerFamily: 'ollama',
    mode: 'hosted',
    baseUrl: 'https://ollama.internal.example.com',
    authMethod: 'api_key',
    apiKeyConfigured: true,
    status: 'connected',
    preferredModel: 'llama3.1:70b-instruct-q4_K_M',
    lastChecked: '5 min ago',
    description: 'Remote Ollama endpoint on a shared GPU cluster for burst overflow, deep analysis, and long-context review.',
    capabilities: { generation: true, embeddings: true, reranking: false, structuredOutputs: true, vision: false, toolCalling: false, streaming: true },
    role: 'burst_overflow',
    workflowFit: ['document-review', 'comparison', 'action-plan'],
    usageNote: 'Burst overflow when local is unavailable. Also used as primary for deep review profiles.',
  },
  {
    id: 'huggingface',
    name: 'Hugging Face Inference',
    providerFamily: 'huggingface',
    mode: 'cloud',
    baseUrl: 'https://api-inference.huggingface.co',
    authMethod: 'bearer_token',
    apiKeyConfigured: true,
    status: 'connected',
    preferredModel: 'mistralai/Mixtral-8x7B-Instruct-v0.1',
    lastChecked: '8 min ago',
    description: 'Optional cloud endpoint for benchmarks, evals, and long-context review when workspace policy allows escalation.',
    capabilities: { generation: true, embeddings: true, reranking: false, structuredOutputs: false, vision: false, toolCalling: false, streaming: true },
    role: 'long_context',
    workflowFit: ['document-review', 'comparison', 'chat-experiments', 'workflow-inspector'],
    usageNote: 'Cloud endpoint kept available for optional hosted usage and benchmark comparisons.',
  },
  {
    id: 'openai-compat',
    name: 'OpenAI-Compatible Endpoint',
    providerFamily: 'openai_compatible',
    mode: 'openai-compatible',
    baseUrl: 'https://api.external-llm.example.com/v1',
    authMethod: 'api_key',
    apiKeyConfigured: false,
    status: 'not_configured',
    preferredModel: 'gpt-4o-mini',
    lastChecked: 'Never',
    description: 'Generic OpenAI-compatible reference endpoint for future benchmark comparisons and external integrations.',
    capabilities: { generation: true, embeddings: true, reranking: false, structuredOutputs: true, vision: true, toolCalling: true, streaming: true },
    role: 'benchmark_reference',
    workflowFit: ['chat-experiments', 'workflow-inspector'],
    usageNote: 'External reference for side-by-side comparison. Requires API key configuration.',
  },
];

export const ALL_WORKFLOWS = [
  { id: 'document-review', label: 'Document Review' },
  { id: 'comparison', label: 'Comparison' },
  { id: 'action-plan', label: 'Action Plan' },
  { id: 'candidate-review', label: 'Candidate Review' },
  { id: 'chat-experiments', label: 'Chat Experiments' },
  { id: 'workflow-inspector', label: 'Workflow Inspector' },
] as const;

export const RUNTIME_PROFILES: RuntimeProfile[] = [
  {
    id: 'current-product-runtime',
    name: 'Current Product Runtime',
    primaryConnectionId: 'ollama-hosted',
    primaryModel: 'nemotron-3-super:cloud',
    fallbackEnabled: false,
    fallbackChain: [],
    executionPolicy: 'hosted_generation_local_embeddings',
    retrievalStrategy: 'hybrid',
    embeddingConnectionId: 'ollama-local',
    embeddingModel: 'embeddinggemma:300m',
    rerankingEnabled: true,
    docProcessingPreset: 'standard',
    qualityPosture: 'low_latency',
    intendedWorkflows: ALL_WORKFLOWS.map((workflow) => workflow.id),
    isActive: true,
    isDefault: true,
    summary: 'Hosted Ollama generation profile using Nemotron 3 Super Cloud with local Ollama embeddings and the standard document processing stack.',
    generation: { temperature: 0.2, contextWindow: 'auto', promptProfile: 'neutro', streaming: true, maxOutputTokens: 4352, topP: 0.95, structuredOutput: false },
    retrieval: { topK: 15, chunkSize: 1200, chunkOverlap: 200, rerankPoolSize: 50, rerankLexicalWeight: 0.3, groundingStrictness: 'balanced' },
    docProcessing: { pdfExtractionMode: 'hybrid', ocrBackend: 'ocrmypdf', vlmEnhancement: false, tableExtractionMode: 'auto', ocrFailoverEnabled: true, scannedDocumentThreshold: 0.6 },
    workflowFit: [],
  },
  {
    id: 'deep-review',
    name: 'Demo Profile',
    primaryConnectionId: 'ollama-hosted',
    primaryModel: 'nemotron-3-nano:30b-cloud',
    fallbackEnabled: false,
    fallbackChain: [],
    executionPolicy: 'hosted_only',
    retrievalStrategy: 'hybrid',
    embeddingConnectionId: 'huggingface',
    embeddingModel: 'BAAI/bge-small-en-v1.5',
    rerankingEnabled: true,
    docProcessingPreset: 'standard',
    qualityPosture: 'low_latency',
    intendedWorkflows: ALL_WORKFLOWS.map((workflow) => workflow.id),
    isActive: false,
    isDefault: true,
    summary: 'Live demo profile using hosted Ollama Nemotron 3 Nano 30B Cloud with Hugging Face BGE-small embeddings for predictable low-latency runs.',
    generation: { temperature: 0.2, contextWindow: 'auto', promptProfile: 'neutro', streaming: true, maxOutputTokens: 4352, topP: 0.95, structuredOutput: false },
    retrieval: { topK: 15, chunkSize: 1200, chunkOverlap: 200, rerankPoolSize: 50, rerankLexicalWeight: 0.3, groundingStrictness: 'balanced' },
    docProcessing: { pdfExtractionMode: 'hybrid', ocrBackend: 'ocrmypdf', vlmEnhancement: false, tableExtractionMode: 'auto', ocrFailoverEnabled: true, scannedDocumentThreshold: 0.6 },
    workflowFit: [],
  },
  {
    id: 'local-only',
    name: 'Local Only',
    primaryConnectionId: 'ollama-local',
    primaryModel: 'qwen2.5:7b',
    fallbackEnabled: false,
    fallbackChain: [],
    executionPolicy: 'local_only',
    retrievalStrategy: 'hybrid',
    embeddingConnectionId: 'ollama-local',
    embeddingModel: 'embeddinggemma:300m',
    rerankingEnabled: true,
    docProcessingPreset: 'standard',
    qualityPosture: 'privacy_first',
    intendedWorkflows: ALL_WORKFLOWS.map((workflow) => workflow.id),
    isActive: false,
    isDefault: true,
    summary: 'Fully local profile for privacy-first runs. Keeps prompts, retrieval, and document context on the local Ollama runtime.',
    generation: { temperature: 0.2, contextWindow: 'auto', promptProfile: 'neutro', streaming: true, maxOutputTokens: 4352, topP: 0.95, structuredOutput: false },
    retrieval: { topK: 15, chunkSize: 1200, chunkOverlap: 200, rerankPoolSize: 50, rerankLexicalWeight: 0.3, groundingStrictness: 'balanced' },
    docProcessing: { pdfExtractionMode: 'hybrid', ocrBackend: 'ocrmypdf', vlmEnhancement: false, tableExtractionMode: 'auto', ocrFailoverEnabled: true, scannedDocumentThreshold: 0.6 },
    workflowFit: [],
  },
];

export const CONNECTION_POLICY_RULES: ConnectionPolicyRule[] = [
  { id: 'allow-hosted-overflow', label: 'Allow hosted burst overflow', description: 'When local GPU is unavailable, production profiles may burst to hosted Ollama.', enabled: true },
  { id: 'hosted-deep-review', label: 'Allow hosted for deep review', description: 'Hosted connections may be used as primary for high-depth review profiles.', enabled: true },
  { id: 'cloud-selected-workflows', label: 'Allow cloud for selected workflows', description: 'Cloud providers such as Hugging Face may be used when explicitly assigned by profile.', enabled: false },
  { id: 'cloud-benchmarks-only', label: 'Restrict cloud to benchmarks/evals', description: 'When enabled, cloud reference models are limited to benchmark and eval workflows.', enabled: true },
  { id: 'require-structured-inspector', label: 'Require structured output for Inspector', description: 'Workflow Inspector should resolve to a connection supporting structured outputs.', enabled: true },
  { id: 'require-evidence-strict', label: 'Require evidence-safe review defaults', description: 'Document Review and Comparison should stay within balanced or strict grounding.', enabled: true },
];

export const DEFAULT_OPERATOR_PREFERENCES: OperatorPreferences = {
  reducedMotion: false,
  defaultEvidencePanelOpen: true,
  defaultExportFormat: 'pdf',
  defaultBenchmarkBaseline: 'current-product-runtime',
  showSourceBadges: true,
  autoOpenInspectorDetails: false,
};

export function getConnection(id: string): ProviderConnection | undefined {
  return PROVIDER_CONNECTIONS.find((connection) => connection.id === id);
}

export function getProfile(id: string): RuntimeProfile | undefined {
  return RUNTIME_PROFILES.find((profile) => profile.id === id);
}

export function getActiveProfile(): RuntimeProfile {
  return RUNTIME_PROFILES.find((profile) => profile.isActive) ?? RUNTIME_PROFILES[0];
}

export const EXECUTION_POLICY_LABELS: Record<string, { label: string; description: string }> = {
  local_only: { label: 'Local Only', description: 'Strictly local execution. Fail hard if unavailable.' },
  prefer_local_burst_hosted: { label: 'Prefer Local · Burst to Hosted', description: 'Uses local GPU first and bursts to hosted only when needed.' },
  hosted_only: { label: 'Hosted Only', description: 'Always uses a remote hosted endpoint.' },
  hosted_generation_local_embeddings: { label: 'Hosted Generation · Local Embeddings', description: 'Uses hosted generation while retrieval embeddings stay on local Ollama.' },
  hosted_deep_review: { label: 'Hosted · Deep Review', description: 'Hosted cluster is primary for deep analysis, with local fallback.' },
  cloud_reference_only: { label: 'Cloud Reference Only', description: 'Cloud provider intended for benchmark and eval reference.' },
  cloud_selected_workflows: { label: 'Cloud · Selected Workflows', description: 'Cloud provider allowed only for explicitly assigned workflows.' },
  benchmark_reference_only: { label: 'Benchmark Reference Only', description: 'External reference used only for side-by-side comparison.' },
};

export const QUALITY_POSTURE_LABELS: Record<string, string> = {
  max_quality: 'Max Quality',
  balanced: 'Balanced',
  low_latency: 'Low Latency',
  cost_optimized: 'Cost Optimized',
  privacy_first: 'Privacy First',
};

export const DOC_PRESET_LABELS: Record<string, string> = {
  standard: 'Standard',
  ocr_heavy: 'OCR Heavy',
  vlm_enhanced: 'VLM Enhanced',
  fast_text: 'Fast Text',
};

export const CONNECTION_ROLE_LABELS: Record<string, string> = {
  production: 'Production',
  benchmark_reference: 'Benchmark',
  burst_overflow: 'Burst / Overflow',
  local_dev: 'Local Dev',
  deep_review: 'Deep Review',
  long_context: 'Long Context',
};

export const COMPATIBILITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  recommended: { bg: 'bg-glow-success/10', text: 'text-glow-success', border: 'border-glow-success/20' },
  compatible: { bg: 'bg-primary/10', text: 'text-primary', border: 'border-primary/20' },
  restricted: { bg: 'bg-glow-warning/10', text: 'text-glow-warning', border: 'border-glow-warning/20' },
  unsupported: { bg: 'bg-glow-error/10', text: 'text-glow-error', border: 'border-glow-error/20' },
};
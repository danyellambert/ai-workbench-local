// Settings types for Runtime Controls and Preferences
// Mock-first architecture ready for future backend integration.

export type ConnectionStatus = 'connected' | 'disconnected' | 'degraded' | 'not_configured';
export type ExecutionTarget = 'local' | 'remote' | 'cloud';
export type RetrievalStrategy = 'hybrid' | 'semantic' | 'lexical';
export type PromptProfile = string;
export type ProviderFamily = 'ollama' | 'huggingface' | 'openai_compatible';
export type ProviderMode = 'local' | 'hosted' | 'cloud' | 'openai-compatible';
export type AuthMethod = 'none' | 'api_key' | 'bearer_token' | 'custom_header';
export type ConnectionRole = 'production' | 'benchmark_reference' | 'burst_overflow' | 'local_dev' | 'deep_review' | 'long_context';
export type ExecutionPolicy =
  | 'local_only'
  | 'prefer_local_burst_hosted'
  | 'hosted_only'
  | 'hosted_deep_review'
  | 'cloud_reference_only'
  | 'cloud_selected_workflows'
  | 'benchmark_reference_only';
export type QualityPosture = 'max_quality' | 'balanced' | 'low_latency' | 'cost_optimized';
export type DocProcessingPreset = 'standard' | 'ocr_heavy' | 'vlm_enhanced' | 'fast_text';
export type GroundingStrictness = 'strict' | 'balanced' | 'permissive';

export interface ProviderCapabilities {
  generation: boolean;
  embeddings: boolean;
  reranking: boolean;
  structuredOutputs: boolean;
  vision: boolean;
  toolCalling: boolean;
  streaming: boolean;
}

export interface ProviderConnection {
  id: string;
  name: string;
  providerFamily: ProviderFamily;
  mode: ProviderMode;
  baseUrl: string;
  authMethod: AuthMethod;
  apiKeyConfigured: boolean;
  status: ConnectionStatus;
  preferredModel: string;
  lastChecked: string;
  description: string;
  capabilities: ProviderCapabilities;
  role: ConnectionRole;
  workflowFit?: string[];
  usageNote?: string;
  credentialManagement?: string;
  supportsCredentialUpdate?: boolean;
  lastErrorMessage?: string;
}

export interface FallbackStep {
  connectionId: string;
  model: string;
  label: string;
}

export interface ProfileGenerationConfig {
  temperature: number;
  contextWindow: string;
  promptProfile: PromptProfile;
  streaming: boolean;
  maxOutputTokens: number;
  topP: number;
  structuredOutput: boolean;
}

export interface ProfileRetrievalConfig {
  topK: number;
  chunkSize: number;
  chunkOverlap: number;
  rerankPoolSize: number;
  rerankLexicalWeight: number;
  groundingStrictness: GroundingStrictness;
}

export interface ProfileDocProcessingConfig {
  pdfExtractionMode: string;
  ocrBackend: string;
  vlmEnhancement: boolean;
  tableExtractionMode: string;
  ocrFailoverEnabled: boolean;
  scannedDocumentThreshold: number;
}

export type WorkflowCompatibility = 'recommended' | 'compatible' | 'restricted' | 'unsupported';

export interface WorkflowFit {
  workflowId: string;
  label: string;
  compatibility: WorkflowCompatibility;
  reason?: string;
}

export interface RuntimeProfile {
  id: string;
  name: string;
  primaryConnectionId: string;
  primaryModel: string;
  fallbackChain: FallbackStep[];
  executionPolicy: ExecutionPolicy;
  retrievalStrategy: RetrievalStrategy;
  embeddingConnectionId: string;
  embeddingModel: string;
  rerankingEnabled: boolean;
  docProcessingPreset: DocProcessingPreset;
  qualityPosture: QualityPosture;
  intendedWorkflows: string[];
  isActive: boolean;
  isDefault: boolean;
  summary: string;
  generation: ProfileGenerationConfig;
  retrieval: ProfileRetrievalConfig;
  docProcessing: ProfileDocProcessingConfig;
  workflowFit: WorkflowFit[];
}

export interface WorkflowDefault {
  workflowId: string;
  label: string;
  profileId: string;
}

export interface ConnectionPolicyRule {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
}

export interface OperatorPreferences {
  reducedMotion: boolean;
  defaultEvidencePanelOpen: boolean;
  defaultExportFormat: 'pdf' | 'markdown' | 'json' | 'pptx';
  defaultBenchmarkBaseline: string;
  showSourceBadges: boolean;
  autoOpenInspectorDetails: boolean;
}
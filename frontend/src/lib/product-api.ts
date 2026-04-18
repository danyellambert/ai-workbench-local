import type {
  ConnectionPolicyRule,
  OperatorPreferences,
  ProviderConnection,
  RuntimeProfile,
  WorkflowDefault,
} from '@/types/settings';

const rawBaseUrl = (import.meta.env.VITE_PRODUCT_API_BASE_URL as string | undefined)?.trim();

export const PRODUCT_API_BASE_URL = (rawBaseUrl || "http://127.0.0.1:8011").replace(/\/$/, "");

export interface CommandCenterSummary {
  indexed_documents: number;
  total_chunks: number;
  completed_runs: number;
  artifacts_generated: number;
  total_chars?: number;
  workflow_count?: number;
}

export interface ProductRunEntry {
  id: string;
  timestamp?: string | null;
  workflow_id?: string;
  workflow_label: string;
  status: string;
  provider?: string | null;
  model?: string | null;
  duration_s?: number | null;
  duration_label?: string | null;
  documents: string[];
  document_count?: number;
  findings_count?: number | null;
  warning_count?: number | null;
  recommendation?: string | null;
  artifacts?: string[];
  error_message?: string | null;
}

export interface ProductArtifactEntry {
  id: string;
  name: string;
  type: string;
  workflow_label: string;
  created_at?: string | null;
  size: string;
  status: string;
  export_kind?: string;
  local_artifact_dir?: string | null;
  local_pptx_path?: string | null;
}

export interface ProductCommandCenterResponse {
  ok: boolean;
  summary: CommandCenterSummary;
  recent_runs: ProductRunEntry[];
  recent_artifacts: ProductArtifactEntry[];
}

export interface ProductRunHistoryResponse {
  ok: boolean;
  source?: string;
  history_path?: string;
  summary: {
    total_runs: number;
    completed_runs: number;
    warning_runs: number;
    error_runs: number;
    workflow_counts: Record<string, number>;
    latest_timestamp?: string | null;
  };
  runs: ProductRunEntry[];
}

export interface ProductArtifactsResponse {
  ok: boolean;
  artifact_root?: string;
  summary: {
    total_artifacts: number;
    completed_artifacts: number;
    error_artifacts: number;
  };
  artifacts: ProductArtifactEntry[];
}

export interface ProductDocumentLibraryEntry {
  document_id: string;
  name: string;
  file_type?: string | null;
  char_count: number;
  chunk_count: number;
  indexed_at?: string | null;
  loader_strategy_label?: string | null;
  status: string;
  size_bytes?: number | null;
  size_label?: string | null;
  warnings: string[];
  source_type?: string | null;
  page_count?: number | null;
}

export interface ProductDocumentLibraryResponse {
  ok: boolean;
  summary: {
    total_documents: number;
    indexed_documents: number;
    warning_documents: number;
    error_documents: number;
    pending_documents: number;
    indexing_documents: number;
    total_chunks: number;
    total_chars: number;
  };
  documents: ProductDocumentLibraryEntry[];
}

export interface ProductUploadDocumentsResponse {
  ok: boolean;
  job_id: string;
  status: string;
  uploaded_count: number;
  ignored_count?: number;
  message?: string;
  current_stage?: string | null;
  steps: Array<{
    key: string;
    label: string;
    status: string;
    detail?: string | null;
    updated_at?: string;
    metadata?: Record<string, unknown>;
  }>;
  index_status?: Record<string, unknown>;
  indexed_documents?: ProductDocumentLibraryEntry[];
  document_library?: ProductDocumentLibraryResponse;
  error?: string | null;
}

export interface ProductDeleteDocumentsResponse {
  ok: boolean;
  removed_count: number;
  removed_document_ids: string[];
  message?: string;
  sync_status?: Record<string, unknown> | null;
  documents: ProductDocumentLibraryEntry[];
  document_library?: ProductDocumentLibraryResponse;
}

export interface ProductGroundingPreview {
  strategy: string;
  document_ids: string[];
  context_chars: number;
  source_block_count: number;
  preview_text: string;
  warnings: string[];
}

export interface ProductGroundingPreviewResponse {
  ok: boolean;
  preview: ProductGroundingPreview;
}

export interface ProductStructuredResultPayload {
  success?: boolean;
  validated_output?: Record<string, unknown> | null;
  raw_output_text?: string | null;
  validation_error?: string | null;
  parsing_error?: string | null;
  overall_confidence?: number | null;
  quality_score?: number | null;
  execution_metadata?: Record<string, unknown>;
}

export interface ProductWorkflowArtifact {
  artifact_type: string;
  label: string;
  path?: string | null;
  download_name?: string | null;
  available: boolean;
}

export interface ProductDocumentReviewFinding {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  title: string;
  description: string;
  source: string;
  chunkId: string;
  confidence: number;
  recommendation: string;
  snippet?: string;
}

export interface ProductDocumentReviewView {
  decision_summary: {
    label: string;
    status: string;
    summary: string;
    severity_counts: Record<'critical' | 'high' | 'medium' | 'low', number>;
    next_owner?: string | null;
    due_date?: string | null;
  };
  document_metrics: {
    strategy?: string | null;
    document_ids: string[];
    context_chars: number;
    source_block_count: number;
  };
  watchouts: string[];
  next_steps: string[];
  top_blockers: Array<{
    title?: string;
    severity?: string;
    recommendation?: string;
  }>;
  business_impact: Array<{
    label: string;
    detail: string;
  }>;
  findings: ProductDocumentReviewFinding[];
  evidence_trail: Array<{
    id?: string;
    severity?: string;
    title?: string;
    chunkId?: string;
    source?: string;
    snippet?: string;
  }>;
  artifacts: ProductWorkflowArtifact[];
  sources: string[][];
  run_state: {
    current_step: string;
    steps: Array<{
      key: string;
      label: string;
      status: string;
    }>;
  };
}

export type ProductPolicyComparisonImpact = 'breaking' | 'significant' | 'minor';

export interface ProductPolicyComparisonDiff {
  id: string;
  clause: string;
  impact: ProductPolicyComparisonImpact;
  category: string;
  doc_a_label: string;
  doc_a_text: string;
  doc_b_label: string;
  doc_b_text: string;
  business_impact: string;
  recommendation?: string | null;
  evidence: string[];
}

export interface ProductPolicyComparisonView {
  compared_documents: string[];
  executive_summary: {
    narrative: string;
    counts: Record<ProductPolicyComparisonImpact, number>;
    status: string;
    documents: string[];
  };
  must_fix_items: Array<{
    title?: string;
    detail?: string;
    impact?: ProductPolicyComparisonImpact;
    recommendation?: string | null;
  }>;
  negotiation_priorities: string[];
  differences: ProductPolicyComparisonDiff[];
  recommendation: {
    summary: string;
    handoff: string;
    artifact_label?: string | null;
  };
  artifacts: ProductWorkflowArtifact[];
  watchouts: string[];
  next_steps: string[];
  run_state: {
    current_step: string;
    steps: Array<{
      key: string;
      label: string;
      status: string;
    }>;
  };
}

export type ProductActionPlanPriority = 'critical' | 'high' | 'medium' | 'low';
export type ProductActionPlanStatus = 'open' | 'in_progress' | 'blocked' | 'done';
export type ProductActionPlanEvidenceGapStatus = 'sufficient' | 'partial' | 'missing';

export interface ProductActionPlanItem {
  id: string;
  title: string;
  owner?: string | null;
  due_date?: string | null;
  priority: ProductActionPlanPriority;
  status: ProductActionPlanStatus;
  source?: string | null;
  evidence?: string | null;
  rationale?: string | null;
  notes?: string | null;
  document_id?: string | null;
}

export interface ProductActionPlanEvidenceGap {
  id: string;
  item_id?: string | null;
  title: string;
  detail: string;
  status: ProductActionPlanEvidenceGapStatus;
  source?: string | null;
  notes?: string | null;
}

export interface ProductActionPlanSummary {
  total: number;
  open: number;
  in_progress: number;
  blocked: number;
  done: number;
  completed: number;
  critical_path: number;
  evidence_gaps: number;
  documents: number;
  artifacts: number;
}

export interface ProductActionPlanRunMetadata {
  workflow_id: string;
  workflow_label: string;
  status: string;
  provider?: string | null;
  model?: string | null;
  context_strategy?: string | null;
  deck_available: boolean;
  deck_export_kind?: string | null;
  warning_count: number;
  warnings: string[];
  source_block_count: number;
  highlights: string[];
  summary: string;
  recommendation?: string | null;
  run_state: {
    current_step: string;
    steps: Array<{
      key: string;
      label: string;
      status: string;
    }>;
  };
}

export interface ProductActionPlanView {
  objective: string;
  summary: ProductActionPlanSummary;
  items: ProductActionPlanItem[];
  critical_path: ProductActionPlanItem[];
  evidence_gaps: ProductActionPlanEvidenceGap[];
  artifacts: ProductWorkflowArtifact[];
  document_ids: string[];
  run_metadata: ProductActionPlanRunMetadata;
}

export interface ProductWorkflowResultPayload {
  workflow_id: string;
  workflow_label: string;
  status: 'completed' | 'warning' | 'error';
  summary: string;
  highlights: string[];
  recommendation?: string | null;
  structured_result?: ProductStructuredResultPayload | null;
  grounding_preview?: ProductGroundingPreview | null;
  artifacts: ProductWorkflowArtifact[];
  deck_export_kind?: string | null;
  deck_available?: boolean;
  warnings: string[];
  debug_metadata?: Record<string, unknown>;
}

export interface ProductRunWorkflowResponse {
  ok: boolean;
  result: ProductWorkflowResultPayload;
  result_view?: ProductDocumentReviewView;
  comparison_view?: ProductPolicyComparisonView;
  action_plan_view?: ProductActionPlanView;
}

export interface ProductGenerateDeckResponse {
  ok: boolean;
  export_result: Record<string, unknown>;
  artifacts: ProductWorkflowArtifact[];
}

export interface ProductPublishTrelloListBreakdown {
  list_id?: string | null;
  list_label: string;
  count: number;
}

export interface ProductPublishTrelloResponse {
  ok: boolean;
  status: string;
  dry_run: boolean;
  workflow_id?: string;
  workflow_label?: string;
  card_mode?: string | null;
  message?: string | null;
  target_board_id?: string | null;
  planned_card_count?: number;
  created_card_count?: number;
  planned_cards?: Array<Record<string, unknown>>;
  created_cards?: Array<Record<string, unknown>>;
  created_card_urls?: string[];
  list_breakdown?: ProductPublishTrelloListBreakdown[];
}


export interface RuntimeControlsCatalogItem {
  value: string;
  label: string;
  description?: string;
  context_window?: number | null;
}

export interface RuntimeControlsCatalogs {
  executionPolicies: RuntimeControlsCatalogItem[];
  qualityPostures: RuntimeControlsCatalogItem[];
  docPresets: RuntimeControlsCatalogItem[];
  retrievalStrategies: RuntimeControlsCatalogItem[];
  groundingStrictness: RuntimeControlsCatalogItem[];
  contextWindows: RuntimeControlsCatalogItem[];
  pdfExtractionModes: RuntimeControlsCatalogItem[];
  ocrBackends: RuntimeControlsCatalogItem[];
  tableExtractionModes: RuntimeControlsCatalogItem[];
  promptProfiles: RuntimeControlsCatalogItem[];
}

export interface RuntimeControlsOptions {
  modelsByConnection: Record<string, string[]>;
  embeddingModelsByConnection: Record<string, string[]>;
}

export interface RuntimeControlsResponse {
  ok: boolean;
  contract_version: string;
  data_source: string;
  updated_at?: string | null;
  active_profile: RuntimeProfile;
  available_connections: ProviderConnection[];
  catalogs: RuntimeControlsCatalogs;
  options: RuntimeControlsOptions;
}

export interface RuntimeControlsPatchPayload {
  profile: Partial<RuntimeProfile>;
}

export interface PreferencesCredentialPolicy {
  mode: string;
  can_update_from_ui: boolean;
  notes: string[];
}

export interface PreferencesResponse {
  ok: boolean;
  contract_version: string;
  updated_at?: string | null;
  active_profile_id: string;
  provider_connections: ProviderConnection[];
  runtime_profiles: RuntimeProfile[];
  workflow_defaults: WorkflowDefault[];
  connection_policy_rules: ConnectionPolicyRule[];
  operator_preferences: OperatorPreferences;
  catalogs: RuntimeControlsCatalogs;
  options: RuntimeControlsOptions;
  credential_policy: PreferencesCredentialPolicy;
}

export interface PreferencesPatchPayload {
  active_profile_id?: string;
  runtime_profiles?: RuntimeProfile[];
  workflow_defaults?: WorkflowDefault[];
  connection_policy_rules?: ConnectionPolicyRule[];
  operator_preferences?: Partial<OperatorPreferences>;
  provider_connections?: Array<Partial<ProviderConnection> & { id: string }>;
}

export interface PreferencesConnectionTestResponse {
  ok: boolean;
  connection_id: string;
  result: {
    status: string;
    checked_at: string;
    latency_ms?: number | null;
    error_message?: string | null;
  };
}

async function fetchProductApi<T>(path: string): Promise<T> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Product API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function patchProductApi<T>(path: string, payload: object): Promise<T> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Product API patch failed: ${response.status}`;
    try {
      const errorPayload = await response.json() as { error?: string };
      if (errorPayload?.error) message = errorPayload.error;
    } catch {
      // ignore JSON parsing error and keep fallback message
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

async function postProductApi<T>(path: string, payload?: object): Promise<T> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: payload ? JSON.stringify(payload) : JSON.stringify({}),
  });
  if (!response.ok) {
    let message = `Product API post failed: ${response.status}`;
    try {
      const errorPayload = await response.json() as { error?: string };
      if (errorPayload?.error) message = errorPayload.error;
    } catch {
      // ignore JSON parsing error and keep fallback message
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function getProductCommandCenter(): Promise<ProductCommandCenterResponse> {
  return fetchProductApi<ProductCommandCenterResponse>("/api/product/command-center");
}

export function getProductRunHistory(): Promise<ProductRunHistoryResponse> {
  return fetchProductApi<ProductRunHistoryResponse>("/api/product/run-history");
}

export function getProductArtifacts(): Promise<ProductArtifactsResponse> {
  return fetchProductApi<ProductArtifactsResponse>("/api/product/artifacts");
}

export function getProductDocumentLibrary(): Promise<ProductDocumentLibraryResponse> {
  return fetchProductApi<ProductDocumentLibraryResponse>("/api/product/document-library");
}

export async function uploadProductDocuments(files: File[]): Promise<ProductUploadDocumentsResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file, file.name);
  }
  const response = await fetch(`${PRODUCT_API_BASE_URL}/api/product/upload-documents`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    let message = `Product API upload failed: ${response.status}`;
    try {
      const errorPayload = await response.json() as { error?: string };
      if (errorPayload?.error) message = errorPayload.error;
    } catch {
      // ignore JSON parsing error and keep fallback message
    }
    throw new Error(message);
  }
  return response.json() as Promise<ProductUploadDocumentsResponse>;
}

export function getProductUploadJob(jobId: string): Promise<ProductUploadDocumentsResponse> {
  return fetchProductApi<ProductUploadDocumentsResponse>(`/api/product/upload-jobs/${encodeURIComponent(jobId)}`);
}

export async function getProductGroundingPreview(params: {
  workflowId: string;
  strategy?: 'document_scan' | 'retrieval';
  documentIds?: string[];
  inputText?: string;
}): Promise<ProductGroundingPreviewResponse> {
  const query = new URLSearchParams();
  query.set('workflow_id', params.workflowId);
  query.set('strategy', params.strategy || 'document_scan');
  for (const documentId of params.documentIds || []) {
    if (documentId) query.append('document_id', documentId);
  }
  if ((params.inputText || '').trim()) {
    query.set('input_text', (params.inputText || '').trim());
  }
  return fetchProductApi<ProductGroundingPreviewResponse>(`/api/product/grounding-preview?${query.toString()}`);
}

export async function runProductWorkflow(payload: {
  workflow_id: string;
  document_ids: string[];
  input_text?: string;
  provider?: string;
  model?: string | null;
  temperature?: number;
  context_window_mode?: 'auto' | 'manual';
  context_window?: number | null;
  use_document_context?: boolean;
  context_strategy?: 'document_scan' | 'retrieval';
}): Promise<ProductRunWorkflowResponse> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}/api/product/run-workflow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Product API workflow failed: ${response.status}`;
    try {
      const errorPayload = await response.json() as { error?: string };
      if (errorPayload?.error) message = errorPayload.error;
    } catch {
      // ignore JSON parsing error and keep fallback message
    }
    throw new Error(message);
  }
  return response.json() as Promise<ProductRunWorkflowResponse>;
}

export async function generateProductWorkflowDeck(result: ProductWorkflowResultPayload): Promise<ProductGenerateDeckResponse> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}/api/product/generate-deck`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result }),
  });
  if (!response.ok) {
    let message = `Product API deck generation failed: ${response.status}`;
    try {
      const errorPayload = await response.json() as { error?: string };
      if (errorPayload?.error) message = errorPayload.error;
    } catch {
      // ignore JSON parsing error and keep fallback message
    }
    throw new Error(message);
  }
  return response.json() as Promise<ProductGenerateDeckResponse>;
}


export async function publishProductWorkflowToTrello(result: ProductWorkflowResultPayload): Promise<ProductPublishTrelloResponse> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}/api/product/publish-trello`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result }),
  });
  if (!response.ok) {
    let message = `Product API Trello publish failed: ${response.status}`;
    try {
      const errorPayload = await response.json() as { error?: string };
      if (errorPayload?.error) message = errorPayload.error;
    } catch {
      // ignore JSON parsing error and keep fallback message
    }
    throw new Error(message);
  }
  return response.json() as Promise<ProductPublishTrelloResponse>;
}

export function buildProductArtifactUrl(path: string): string {
  const params = new URLSearchParams({ path });
  return `${PRODUCT_API_BASE_URL}/api/product/artifact?${params.toString()}`;
}

export async function deleteProductDocuments(documentIds: string[]): Promise<ProductDeleteDocumentsResponse> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}/api/product/delete-documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds }),
  });
  if (!response.ok) {
    let message = `Product API delete failed: ${response.status}`;
    try {
      const errorPayload = await response.json() as { error?: string };
      if (errorPayload?.error) message = errorPayload.error;
    } catch {
      // ignore JSON parsing error and keep fallback message
    }
    throw new Error(message);
  }
  return response.json() as Promise<ProductDeleteDocumentsResponse>;
}

export function getRuntimeControls(): Promise<RuntimeControlsResponse> {
  return fetchProductApi<RuntimeControlsResponse>('/api/runtime/controls');
}

export function updateRuntimeControls(payload: RuntimeControlsPatchPayload): Promise<RuntimeControlsResponse> {
  return patchProductApi<RuntimeControlsResponse>('/api/runtime/controls', payload);
}

export function getPreferences(): Promise<PreferencesResponse> {
  return fetchProductApi<PreferencesResponse>('/api/preferences');
}

export function updatePreferences(payload: PreferencesPatchPayload): Promise<PreferencesResponse> {
  return patchProductApi<PreferencesResponse>('/api/preferences', payload);
}

export function testPreferencesConnection(connectionId: string): Promise<PreferencesConnectionTestResponse> {
  return postProductApi<PreferencesConnectionTestResponse>(`/api/preferences/connections/${encodeURIComponent(connectionId)}/test`);
}

export function updatePreferencesConnectionCredential(connectionId: string, apiKey: string): Promise<PreferencesResponse> {
  return postProductApi<PreferencesResponse>(`/api/preferences/connections/${encodeURIComponent(connectionId)}/credential`, { api_key: apiKey });
}
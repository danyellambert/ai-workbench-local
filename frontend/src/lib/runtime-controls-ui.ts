import type { ProviderCapabilities, ProviderConnection, RuntimeProfile, WorkflowFit } from '@/types/settings';
import type { RuntimeControlsCatalogItem, RuntimeControlsResponse } from '@/lib/product-api';

export const RUNTIME_COMPATIBILITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  recommended: { bg: 'bg-glow-success/10', text: 'text-glow-success', border: 'border-glow-success/20' },
  compatible: { bg: 'bg-primary/10', text: 'text-primary', border: 'border-primary/20' },
  restricted: { bg: 'bg-glow-warning/10', text: 'text-glow-warning', border: 'border-glow-warning/20' },
  unsupported: { bg: 'bg-glow-error/10', text: 'text-glow-error', border: 'border-glow-error/20' },
};

export const EMPTY_PROVIDER_CAPABILITIES: ProviderCapabilities = {
  generation: false,
  embeddings: false,
  reranking: false,
  structuredOutputs: false,
  vision: false,
  toolCalling: false,
  streaming: false,
};

export function cloneRuntimeProfile(profile: RuntimeProfile): RuntimeProfile {
  return JSON.parse(JSON.stringify(profile)) as RuntimeProfile;
}

export function buildCatalogLookup(items: RuntimeControlsCatalogItem[] | undefined): Record<string, RuntimeControlsCatalogItem> {
  return Object.fromEntries((items || []).map((item) => [item.value, item]));
}

export function getRuntimeConnection(payload: RuntimeControlsResponse | undefined, id: string): ProviderConnection | undefined {
  return payload?.available_connections.find((connection) => connection.id === id);
}

export function formatRuntimeUpdatedAt(value?: string | null): string {
  if (!value) return 'Not saved yet';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function deriveRuntimeFallbackChain(profile: RuntimeProfile, payload: RuntimeControlsResponse | undefined) {
  const connections = payload?.available_connections ?? [];
  const modelsByConnection = payload?.options.modelsByConnection ?? {};
  return connections
    .filter((connection) => connection.id !== profile.primaryConnectionId)
    .filter((connection) => connection.capabilities.generation)
    .filter((connection) => connection.status === 'connected')
    .slice(0, 2)
    .map((connection) => ({
      connectionId: connection.id,
      model: (modelsByConnection[connection.id] || [connection.preferredModel]).filter(Boolean)[0] || connection.preferredModel,
      label: `Fallback to ${connection.name}`,
    }));
}

export function deriveRuntimeWorkflowFit(profile: RuntimeProfile, primaryConnection: ProviderConnection | undefined): WorkflowFit[] {
  void primaryConnection;
  return profile.workflowFit ?? [];
}
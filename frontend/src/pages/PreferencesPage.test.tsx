import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PreferencesPage from '@/pages/PreferencesPage';
import { getPreferences, testPreferencesConnection, updatePreferences, type PreferencesResponse } from '@/lib/product-api';

vi.mock('@/components/ui/sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/lib/product-api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/product-api')>('@/lib/product-api');
  return {
    ...actual,
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    testPreferencesConnection: vi.fn(),
  };
});

function buildPreferencesResponse(activeProfileId = 'workspace-default'): PreferencesResponse {
  return {
    ok: true,
    contract_version: 'preferences.v1',
    updated_at: '2026-04-16T13:00:00+00:00',
    active_profile_id: activeProfileId,
    provider_connections: [
      {
        id: 'ollama',
        name: 'Ollama (local)',
        providerFamily: 'ollama',
        mode: 'local',
        baseUrl: 'http://127.0.0.1:11434',
        authMethod: 'none',
        apiKeyConfigured: false,
        status: 'connected',
        preferredModel: 'qwen2.5:7b',
        lastChecked: '2026-04-16T13:00:00+00:00',
        description: 'Primary local runtime.',
        capabilities: {
          generation: true,
          embeddings: true,
          reranking: false,
          structuredOutputs: true,
          vision: false,
          toolCalling: false,
          streaming: true,
        },
        role: 'production',
        workflowFit: ['document-review', 'comparison'],
        usageNote: 'Primary workspace connection.',
        credentialManagement: 'not_required',
        supportsCredentialUpdate: false,
      },
    ],
    runtime_profiles: [
      {
        id: 'workspace-default',
        name: 'Workspace Default',
        primaryConnectionId: 'ollama',
        primaryModel: 'qwen2.5:7b',
        fallbackChain: [],
        executionPolicy: 'local_only',
        retrievalStrategy: 'hybrid',
        embeddingConnectionId: 'ollama',
        embeddingModel: 'embeddinggemma:300m',
        rerankingEnabled: true,
        docProcessingPreset: 'standard',
        qualityPosture: 'balanced',
        intendedWorkflows: ['document-review'],
        isActive: activeProfileId === 'workspace-default',
        isDefault: true,
        summary: 'Workspace default summary.',
        generation: {
          temperature: 0.2,
          contextWindow: 'auto',
          promptProfile: 'neutro',
          streaming: true,
          maxOutputTokens: 4096,
          topP: 0.95,
          structuredOutput: false,
        },
        retrieval: {
          topK: 8,
          chunkSize: 1200,
          chunkOverlap: 120,
          rerankPoolSize: 16,
          rerankLexicalWeight: 0.3,
          groundingStrictness: 'balanced',
        },
        docProcessing: {
          pdfExtractionMode: 'hybrid',
          ocrBackend: 'ocrmypdf',
          vlmEnhancement: false,
          tableExtractionMode: 'auto',
          ocrFailoverEnabled: true,
          scannedDocumentThreshold: 0.7,
        },
        workflowFit: [
          { workflowId: 'document-review', label: 'Document Review', compatibility: 'recommended' },
        ],
      },
      {
        id: 'deep-review',
        name: 'Deep Review',
        primaryConnectionId: 'ollama',
        primaryModel: 'qwen2.5:7b',
        fallbackChain: [],
        executionPolicy: 'prefer_local_burst_hosted',
        retrievalStrategy: 'hybrid',
        embeddingConnectionId: 'ollama',
        embeddingModel: 'embeddinggemma:300m',
        rerankingEnabled: true,
        docProcessingPreset: 'ocr_heavy',
        qualityPosture: 'max_quality',
        intendedWorkflows: ['document-review', 'comparison'],
        isActive: activeProfileId === 'deep-review',
        isDefault: false,
        summary: 'Deep review summary.',
        generation: {
          temperature: 0.25,
          contextWindow: '32k',
          promptProfile: 'neutro',
          streaming: true,
          maxOutputTokens: 8192,
          topP: 0.95,
          structuredOutput: false,
        },
        retrieval: {
          topK: 16,
          chunkSize: 1400,
          chunkOverlap: 120,
          rerankPoolSize: 24,
          rerankLexicalWeight: 0.25,
          groundingStrictness: 'strict',
        },
        docProcessing: {
          pdfExtractionMode: 'complete',
          ocrBackend: 'ocrmypdf',
          vlmEnhancement: true,
          tableExtractionMode: 'auto',
          ocrFailoverEnabled: true,
          scannedDocumentThreshold: 0.5,
        },
        workflowFit: [
          { workflowId: 'document-review', label: 'Document Review', compatibility: 'recommended' },
        ],
      },
    ],
    workflow_defaults: [
      { workflowId: 'document-review', label: 'Document Review', profileId: 'workspace-default' },
      { workflowId: 'comparison', label: 'Comparison', profileId: 'deep-review' },
    ],
    connection_policy_rules: [
      {
        id: 'allow-hosted-overflow',
        label: 'Allow hosted burst overflow',
        description: 'Allow hosted overflow when local GPU is unavailable.',
        enabled: true,
      },
    ],
    operator_preferences: {
      reducedMotion: false,
      defaultEvidencePanelOpen: true,
      defaultExportFormat: 'pdf',
      defaultBenchmarkBaseline: 'workspace-default',
      showSourceBadges: true,
      autoOpenInspectorDetails: false,
    },
    catalogs: {
      executionPolicies: [
        { value: 'local_only', label: 'Local Only' },
        { value: 'prefer_local_burst_hosted', label: 'Prefer Local · Burst to Hosted' },
      ],
      qualityPostures: [
        { value: 'balanced', label: 'Balanced' },
        { value: 'max_quality', label: 'Max Quality' },
      ],
      docPresets: [
        { value: 'standard', label: 'Standard' },
        { value: 'ocr_heavy', label: 'OCR Heavy' },
      ],
      retrievalStrategies: [{ value: 'hybrid', label: 'Hybrid' }],
      groundingStrictness: [{ value: 'balanced', label: 'Balanced' }],
      contextWindows: [{ value: 'auto', label: 'Auto' }],
      pdfExtractionModes: [{ value: 'hybrid', label: 'Hybrid' }],
      ocrBackends: [{ value: 'ocrmypdf', label: 'OCRmyPDF' }],
      tableExtractionModes: [{ value: 'auto', label: 'Auto' }],
      promptProfiles: [{ value: 'neutro', label: 'Neutro' }],
    },
    options: {
      modelsByConnection: { ollama: ['qwen2.5:7b'] },
      embeddingModelsByConnection: { ollama: ['embeddinggemma:300m'] },
    },
    credential_policy: {
      mode: 'env_only',
      can_update_from_ui: false,
      notes: ['Secrets remain managed outside the UI.'],
    },
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <PreferencesPage />
    </QueryClientProvider>,
  );
}

describe('PreferencesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPreferences).mockResolvedValue(buildPreferencesResponse());
    vi.mocked(updatePreferences).mockImplementation(async (payload) => {
      if (payload.active_profile_id === 'deep-review') {
        return buildPreferencesResponse('deep-review');
      }
      return buildPreferencesResponse();
    });
    vi.mocked(testPreferencesConnection).mockResolvedValue({
      ok: true,
      connection_id: 'ollama',
      result: {
        status: 'connected',
        checked_at: '2026-04-16T13:05:00+00:00',
        latency_ms: 22,
        error_message: null,
      },
    });
  });

  it('loads live preferences, activates a saved profile and tests a provider connection', async () => {
    renderPage();

    expect(await screen.findByText('Live preferences')).toBeInTheDocument();
    expect((await screen.findAllByText('Workspace Default')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('Deep Review')).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: 'Set active' }));
    await waitFor(() => expect(updatePreferences).toHaveBeenCalledWith({ active_profile_id: 'deep-review' }));

    fireEvent.click(screen.getByRole('button', { name: /Test connection/i }));
    await waitFor(() => expect(testPreferencesConnection).toHaveBeenCalledWith('ollama'));
  });
});
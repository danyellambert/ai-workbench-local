import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import RuntimeControlsPage from '@/pages/RuntimeControlsPage';
import {
  getOllamaHostedModels,
  getRuntimeControls,
  updateRuntimeControls,
  type RuntimeControlsResponse,
} from '@/lib/product-api';

vi.mock('@/lib/product-api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/product-api')>('@/lib/product-api');
  return {
    ...actual,
    getRuntimeControls: vi.fn(),
    getOllamaHostedModels: vi.fn(),
    updateRuntimeControls: vi.fn(),
  };
});

vi.mock('@/components/ui/select', () => ({
  Select: ({ children, onOpenChange }: any) => (
    <div data-testid="select-root" onClick={() => onOpenChange?.(true)}>
      {children}
    </div>
  ),
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => <div role="option" data-value={value}>{children}</div>,
  SelectTrigger: ({ children, onClick }: any) => (
    <button type="button" data-testid="select-trigger" onClick={onClick}>
      {children}
    </button>
  ),
  SelectValue: () => <span>Select value</span>,
}));

vi.mock('@/lib/auth-session', () => ({
  useAuthSession: () => ({ data: { ok: true, role: 'admin' }, isLoading: false }),
  isAdminSession: () => true,
}));


beforeAll(() => {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
  }
  if (!Element.prototype.releasePointerCapture) {
    Element.prototype.releasePointerCapture = () => undefined;
  }
  if (!Element.prototype.setPointerCapture) {
    Element.prototype.setPointerCapture = () => undefined;
  }
});

function buildRuntimeControlsResponse(): RuntimeControlsResponse {
  return {
    ok: true,
    contract_version: 'runtime_controls.v1',
    data_source: 'test',
    updated_at: '2026-05-12T00:00:00Z',
    available_connections: [
      {
        id: 'ollama_hosted',
        name: 'Ollama Hosted',
        description: 'Hosted Ollama cloud generation.',
        providerFamily: 'ollama',
        mode: 'hosted',
        role: 'primary',
        status: 'connected',
        baseUrl: 'https://ollama.com/api',
        authMethod: 'api_key',
        apiKeyConfigured: true,
        preferredModel: 'nemotron-3-super:cloud',
        capabilities: {
          generation: true,
          embeddings: false,
          structuredOutputs: true,
          streaming: true,
          vision: false,
          toolCalling: false,
          reranking: false,
        },
      },
      {
        id: 'ollama',
        name: 'Ollama Local',
        description: 'Local Ollama runtime.',
        providerFamily: 'ollama',
        mode: 'local',
        role: 'fallback',
        status: 'connected',
        baseUrl: 'http://localhost:11434/v1',
        authMethod: 'none',
        apiKeyConfigured: false,
        preferredModel: 'qwen2.5:7b',
        capabilities: {
          generation: true,
          embeddings: true,
          structuredOutputs: true,
          streaming: true,
          vision: false,
          toolCalling: false,
          reranking: false,
        },
      },
    ],
    active_profile: {
      id: 'current-product-runtime',
      name: 'Current Product Runtime',
      summary: 'Hosted Ollama generation with local embeddings.',
      isDefault: true,
      isActive: true,
      primaryConnectionId: 'ollama_hosted',
      primaryModel: 'nemotron-3-super:cloud',
      embeddingConnectionId: 'ollama',
      embeddingModel: 'embeddinggemma:300m',
      executionPolicy: 'hosted_generation_local_embeddings',
      qualityPosture: 'balanced',
      retrievalStrategy: 'hybrid',
      docProcessingPreset: 'standard',
      rerankingEnabled: false,
      workflowFit: [],
      fallbackChain: [],
      generation: {
        temperature: 0.2,
        contextWindow: 'auto',
        promptProfile: 'neutro',
        streaming: true,
        maxOutputTokens: 4096,
        topP: 0.95,
        structuredOutput: true,
      },
      retrieval: {
        topK: 12,
        chunkSize: 1200,
        chunkOverlap: 200,
        rerankPoolSize: 0,
        rerankLexicalWeight: 0.3,
        groundingStrictness: 'balanced',
      },
      docProcessing: {
        pdfExtractionMode: 'hybrid',
        ocrBackend: 'ocrmypdf',
        vlmEnhancement: false,
        tableExtractionMode: 'auto',
        ocrFailoverEnabled: true,
        scannedDocumentThreshold: 0.6,
      },
    },
    catalogs: {
      executionPolicies: [{ value: 'hosted_generation_local_embeddings', label: 'Hosted Generation · Local Embeddings' }],
      qualityPostures: [{ value: 'balanced', label: 'Balanced' }],
      docPresets: [{ value: 'standard', label: 'Standard' }],
      retrievalStrategies: [{ value: 'hybrid', label: 'Hybrid' }],
      groundingStrictness: [{ value: 'balanced', label: 'Balanced' }],
      contextWindows: [{ value: 'auto', label: 'Auto', context_window: null }],
      pdfExtractionModes: [{ value: 'hybrid', label: 'Smart hybrid' }],
      ocrBackends: [{ value: 'ocrmypdf', label: 'OCRmyPDF' }],
      tableExtractionModes: [{ value: 'auto', label: 'Auto-detect' }],
      promptProfiles: [{ value: 'neutro', label: 'neutro' }],
    },
    options: {
      modelsByConnection: {
        ollama_hosted: ['nemotron-3-super:cloud', 'nemotron-3-nano:30b-cloud'],
        ollama: ['qwen2.5:7b'],
      },
      embeddingModelsByConnection: {
        ollama: ['embeddinggemma:300m'],
        ollama_hosted: [],
      },
    },
  } as RuntimeControlsResponse;
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
      <RuntimeControlsPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(getRuntimeControls).mockResolvedValue(buildRuntimeControlsResponse());
  vi.mocked(updateRuntimeControls).mockImplementation(async () => buildRuntimeControlsResponse());
  vi.mocked(getOllamaHostedModels).mockResolvedValue({
    ok: true,
    source: 'ollama_hosted_tags',
    default_model: 'nemotron-3-super:cloud',
    models: ['nemotron-3-super:cloud', 'nemotron-3-nano:30b-cloud', 'gpt-oss:120b-cloud'],
    fallback_models: ['nemotron-3-super:cloud', 'nemotron-3-nano:30b-cloud'],
    cached: false,
    error: null,
    updated_at: '2026-05-12T00:00:00Z',
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('RuntimeControlsPage Ollama Hosted model dropdown', () => {
  it('refreshes Ollama Hosted cloud models lazily when the model dropdown opens', async () => {
    renderPage();

    expect(await screen.findByText('Live runtime')).toBeInTheDocument();
    expect(screen.getByText('Open the dropdown to refresh the Ollama Hosted cloud model list.')).toBeInTheDocument();

    const triggers = screen.getAllByTestId('select-trigger');
    fireEvent.click(triggers[1]);

    await waitFor(() => expect(getOllamaHostedModels).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('gpt-oss:120b-cloud')).toBeInTheDocument();
    expect(await screen.findByText('Model list refreshed from Ollama Hosted when the dropdown opened.')).toBeInTheDocument();
  });

  it('keeps Super and Nano fallback visible when Ollama Hosted refresh fails', async () => {
    vi.mocked(getOllamaHostedModels).mockResolvedValueOnce({
      ok: false,
      source: 'fallback',
      default_model: 'nemotron-3-super:cloud',
      models: ['nemotron-3-super:cloud', 'nemotron-3-nano:30b-cloud'],
      fallback_models: ['nemotron-3-super:cloud', 'nemotron-3-nano:30b-cloud'],
      cached: false,
      error: 'Ollama Hosted API key is not configured.',
      updated_at: '2026-05-12T00:00:00Z',
    });

    renderPage();

    expect(await screen.findByText('Live runtime')).toBeInTheDocument();

    const triggers = screen.getAllByTestId('select-trigger');
    fireEvent.click(triggers[1]);

    await waitFor(() => expect(getOllamaHostedModels).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getAllByText('nemotron-3-super:cloud').length).toBeGreaterThan(0));
    await waitFor(() => expect(screen.getAllByText('nemotron-3-nano:30b-cloud').length).toBeGreaterThan(0));
    expect(await screen.findByText('Could not refresh Ollama Hosted models. Showing the safe Nemotron Super/Nano fallback.')).toBeInTheDocument();
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import { getOllamaHostedModels } from './product-api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('getOllamaHostedModels', () => {
  it('loads Ollama Hosted cloud models from the backend proxy endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ok: true,
          source: 'ollama_hosted_tags',
          default_model: 'nemotron-3-super:cloud',
          models: ['nemotron-3-super:cloud', 'gpt-oss:120b-cloud'],
          fallback_models: ['nemotron-3-super:cloud', 'nemotron-3-nano:30b-cloud'],
          cached: false,
          error: null,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    vi.stubGlobal('fetch', fetchMock);

    await expect(getOllamaHostedModels()).resolves.toMatchObject({
      ok: true,
      default_model: 'nemotron-3-super:cloud',
      models: ['nemotron-3-super:cloud', 'gpt-oss:120b-cloud'],
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/runtime/ollama-hosted/models');
  });
});

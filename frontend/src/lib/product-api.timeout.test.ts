import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ProductWorkflowTimeoutRecoveryError,
  isProductWorkflowTimeoutStatus,
  runProductWorkflow,
} from './product-api';

const payload = {
  workflow_id: 'document_review',
  document_ids: ['doc_1'],
  context_strategy: 'retrieval' as const,
  use_document_context: true,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('product workflow timeout recovery', () => {
  it.each([524, 502, 503, 504])('throws a recoverable timeout error for HTTP %s', async (status) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ok: false, error: 'edge timeout' }), {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    await expect(runProductWorkflow(payload)).rejects.toBeInstanceOf(ProductWorkflowTimeoutRecoveryError);

    try {
      await runProductWorkflow(payload);
    } catch (error) {
      expect(error).toBeInstanceOf(ProductWorkflowTimeoutRecoveryError);
      expect((error as ProductWorkflowTimeoutRecoveryError).status).toBe(status);
      expect((error as Error).message).toContain('Run History');
    }
  });

  it('does not classify regular bad requests as timeout recovery errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ok: false, error: 'validation failed' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    await expect(runProductWorkflow(payload)).rejects.toThrow('validation failed');
    await expect(runProductWorkflow(payload)).rejects.not.toBeInstanceOf(ProductWorkflowTimeoutRecoveryError);
  });

  it('recognizes only edge/proxy timeout-like statuses as recoverable', () => {
    expect(isProductWorkflowTimeoutStatus(524)).toBe(true);
    expect(isProductWorkflowTimeoutStatus(502)).toBe(true);
    expect(isProductWorkflowTimeoutStatus(503)).toBe(true);
    expect(isProductWorkflowTimeoutStatus(504)).toBe(true);
    expect(isProductWorkflowTimeoutStatus(400)).toBe(false);
    expect(isProductWorkflowTimeoutStatus(429)).toBe(false);
    expect(isProductWorkflowTimeoutStatus(500)).toBe(false);
  });
});

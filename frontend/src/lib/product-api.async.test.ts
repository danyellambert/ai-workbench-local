import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ProductWorkflowTimeoutRecoveryError,
  runProductWorkflow,
  type ProductRunWorkflowResponse,
} from './product-api';

const payload = {
  workflow_id: 'document_review',
  document_ids: ['doc_1'],
  context_strategy: 'retrieval' as const,
  use_document_context: true,
};

function buildCompletedResponse(): ProductRunWorkflowResponse {
  return {
    ok: true,
    run_id: 'run_document_review_test',
    result: {
      workflow_id: 'document_review',
      workflow_label: 'Document Review',
      status: 'completed',
      summary: 'Completed async workflow.',
      findings: [],
      recommendation: 'Approve',
      artifacts: [],
      grounding_preview: {
        strategy: 'retrieval',
        document_ids: ['doc_1'],
        context_chars: 100,
        source_block_count: 1,
        preview_text: 'Grounded context',
        warnings: [],
      },
      deck_available: false,
      deck_export_kind: 'document_review',
    } as ProductRunWorkflowResponse['result'],
    result_sections: {
      summary: 'Completed async workflow.',
      highlights: [],
      recommendation: 'Approve',
      warnings: [],
      tables: [],
      sources: [],
      artifacts: [],
      strengths: [],
      watchouts: [],
      next_steps: [],
      evidence_highlights: [],
    },
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('product workflow async polling', () => {
  it('returns immediately when the async POST already contains a completed response', async () => {
    const completedResponse = buildCompletedResponse();

    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({
      ok: true,
      job_id: 'workflow_job_fast',
      status: 'completed',
      workflow_id: 'document_review',
      response: completedResponse,
      poll_after_seconds: 0,
    }, 202));

    vi.stubGlobal('fetch', fetchMock);

    await expect(runProductWorkflow(payload)).resolves.toEqual(completedResponse);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/product/run-workflow-async');
  });

  it('starts an async workflow job and returns the completed workflow response after polling', async () => {
    vi.useFakeTimers();

    const completedResponse = buildCompletedResponse();

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_test',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }, 202))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_test',
        status: 'completed',
        workflow_id: 'document_review',
        response: completedResponse,
        poll_after_seconds: 0,
      }));

    vi.stubGlobal('fetch', fetchMock);

    const assertion = expect(runProductWorkflow(payload)).resolves.toEqual(completedResponse);
    await vi.advanceTimersByTimeAsync(2000);
    await assertion;

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/product/run-workflow-async');
    expect(String(fetchMock.mock.calls[1][0])).toContain('/api/product/workflow-jobs/workflow_job_test');
  });

  it('keeps the workflow promise pending while the job is queued/running, then resolves when completed', async () => {
    vi.useFakeTimers();

    const completedResponse = buildCompletedResponse();
    let settled = false;

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_long',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }, 202))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_long',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_long',
        status: 'running',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_long',
        status: 'completed',
        workflow_id: 'document_review',
        response: completedResponse,
        poll_after_seconds: 0,
      }));

    vi.stubGlobal('fetch', fetchMock);

    const promise = runProductWorkflow(payload).finally(() => {
      settled = true;
    });

    await vi.advanceTimersByTimeAsync(2000);
    expect(settled).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(2000);
    expect(settled).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(3);

    await vi.advanceTimersByTimeAsync(2000);
    await expect(promise).resolves.toEqual(completedResponse);
    expect(settled).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it('throws a recoverable timeout error when the initial async POST receives a proxy timeout', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({ ok: false, error: 'edge timeout' }, 524));
    vi.stubGlobal('fetch', fetchMock);

    await expect(runProductWorkflow(payload)).rejects.toBeInstanceOf(ProductWorkflowTimeoutRecoveryError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws a recoverable timeout error when the polling endpoint returns a proxy timeout', async () => {
    vi.useFakeTimers();

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_poll_timeout',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }, 202))
      .mockResolvedValueOnce(jsonResponse({ ok: false, error: 'edge timeout' }, 504));

    vi.stubGlobal('fetch', fetchMock);

    const assertion = expect(runProductWorkflow(payload)).rejects.toBeInstanceOf(ProductWorkflowTimeoutRecoveryError);
    await vi.advanceTimersByTimeAsync(2000);
    await assertion;

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('throws the backend message when polling is forbidden for the current session', async () => {
    vi.useFakeTimers();

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_forbidden',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }, 202))
      .mockResolvedValueOnce(jsonResponse({
        ok: false,
        error: 'Workflow job is not available for this session.',
      }, 403));

    vi.stubGlobal('fetch', fetchMock);

    const assertion = expect(runProductWorkflow(payload)).rejects.toThrow('not available for this session');
    await vi.advanceTimersByTimeAsync(2000);
    await assertion;

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('throws the backend message when polling returns an expired/not-found job', async () => {
    vi.useFakeTimers();

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_expired',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }, 202))
      .mockResolvedValueOnce(jsonResponse({
        ok: false,
        error: 'Workflow job not found or expired.',
      }, 404));

    vi.stubGlobal('fetch', fetchMock);

    const assertion = expect(runProductWorkflow(payload)).rejects.toThrow('not found or expired');
    await vi.advanceTimersByTimeAsync(2000);
    await assertion;

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('throws a clear error if a completed job does not include a workflow response', async () => {
    vi.useFakeTimers();

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_malformed_completed',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }, 202))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_malformed_completed',
        status: 'completed',
        workflow_id: 'document_review',
        poll_after_seconds: 0,
      }));

    vi.stubGlobal('fetch', fetchMock);

    const assertion = expect(runProductWorkflow(payload)).rejects.toThrow('did not return a workflow response');
    await vi.advanceTimersByTimeAsync(2000);
    await assertion;

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('throws a recoverable timeout error when the job stays running beyond the polling window', async () => {
    vi.useFakeTimers();

    const fetchMock = vi.fn(async (url: string) => {
      if (String(url).includes('/api/product/run-workflow-async')) {
        return jsonResponse({
          ok: true,
          job_id: 'workflow_job_never_finishes',
          status: 'queued',
          workflow_id: 'document_review',
          poll_after_seconds: 1,
        }, 202);
      }

      return jsonResponse({
        ok: true,
        job_id: 'workflow_job_never_finishes',
        status: 'running',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      });
    });

    vi.stubGlobal('fetch', fetchMock);

    const assertion = expect(runProductWorkflow(payload)).rejects.toBeInstanceOf(ProductWorkflowTimeoutRecoveryError);
    await vi.advanceTimersByTimeAsync(15 * 60 * 1000 + 5000);
    await assertion;

    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes('/api/product/workflow-jobs/workflow_job_never_finishes'))).toBe(true);
  });

  it('throws a clear error when a background job fails', async () => {
    vi.useFakeTimers();

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        job_id: 'workflow_job_failed',
        status: 'queued',
        workflow_id: 'document_review',
        poll_after_seconds: 1,
      }, 202))
      .mockResolvedValueOnce(jsonResponse({
        ok: false,
        job_id: 'workflow_job_failed',
        status: 'error',
        workflow_id: 'document_review',
        error: 'provider failed',
        poll_after_seconds: 0,
      }));

    vi.stubGlobal('fetch', fetchMock);

    const assertion = expect(runProductWorkflow(payload)).rejects.toThrow('provider failed');
    await vi.advanceTimersByTimeAsync(2000);
    await assertion;

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/product/run-workflow-async');
    expect(String(fetchMock.mock.calls[1][0])).toContain('/api/product/workflow-jobs/workflow_job_failed');
  });

  it('throws a clear error when the async POST accepts no job id and no completed response', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({
      ok: true,
      status: 'queued',
      workflow_id: 'document_review',
    }, 202));

    vi.stubGlobal('fetch', fetchMock);

    await expect(runProductWorkflow(payload)).rejects.toThrow('did not return a workflow job id');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('surfaces initial backend 429 messages instead of polling', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({
      ok: false,
      error: 'You already have a workflow running. Wait for it to finish before starting another one.',
    }, 429));

    vi.stubGlobal('fetch', fetchMock);

    await expect(runProductWorkflow(payload)).rejects.toThrow('already have a workflow running');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

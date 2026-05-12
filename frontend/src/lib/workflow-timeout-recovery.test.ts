import { afterEach, describe, expect, it, vi } from 'vitest';
import type { QueryClient } from '@tanstack/react-query';
import { refreshWorkflowTimeoutRecoveryQueries } from './workflow-timeout-recovery';

afterEach(() => {
  vi.useRealTimers();
});

describe('refreshWorkflowTimeoutRecoveryQueries', () => {
  it('refreshes run history immediately and again after recovery delays', async () => {
    vi.useFakeTimers();

    const invalidateQueries = vi.fn().mockResolvedValue(undefined);
    const queryClient = { invalidateQueries } as unknown as QueryClient;

    await refreshWorkflowTimeoutRecoveryQueries(queryClient);

    expect(invalidateQueries).toHaveBeenCalledTimes(5);
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['product-run-history'] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['product-command-center'] });

    await vi.advanceTimersByTimeAsync(10_000);
    expect(invalidateQueries).toHaveBeenCalledTimes(10);

    await vi.advanceTimersByTimeAsync(20_000);
    expect(invalidateQueries).toHaveBeenCalledTimes(15);

    await vi.advanceTimersByTimeAsync(30_000);
    expect(invalidateQueries).toHaveBeenCalledTimes(20);
  });
});

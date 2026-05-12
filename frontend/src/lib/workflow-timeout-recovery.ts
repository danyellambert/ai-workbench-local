import type { QueryClient } from '@tanstack/react-query';
import { aiLabQueryKeys } from '@/lib/ai-lab-data';

const RECOVERY_REFRESH_DELAYS_MS = [10_000, 30_000, 60_000];

export async function refreshWorkflowTimeoutRecoveryQueries(queryClient: QueryClient): Promise<void> {
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
      queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.evals }),
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.overview }),
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.runtime }),
    ]).then(() => undefined);

  await refresh();

  RECOVERY_REFRESH_DELAYS_MS.forEach((delayMs) => {
    window.setTimeout(() => {
      void refresh();
    }, delayMs);
  });
}

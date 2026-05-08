export type PublicExecutionQuotaPayload = {
  ok?: boolean;
  error?: string;
  message?: string;
  retry_after_seconds?: number;
  reset_at?: string;
  execution_quota?: {
    ok?: boolean;
    message?: string;
    max_per_session?: number;
    window_seconds?: number;
    retry_after_seconds?: number;
    reset_at?: string;
    session_count?: number;
    execution_kind?: string;
  };
};

function formatRetryAfterDuration(seconds: number): string {
  const roundedSeconds = Math.max(1, Math.ceil(seconds));

  if (roundedSeconds < 60) {
    return `${roundedSeconds} second${roundedSeconds === 1 ? '' : 's'}`;
  }

  const minutes = Math.max(1, Math.ceil(roundedSeconds / 60));
  return `${minutes} minute${minutes === 1 ? '' : 's'}`;
}

export class PublicExecutionQuotaError extends Error {
  payload: PublicExecutionQuotaPayload;
  retryAfterSeconds?: number;
  resetAt?: string;

  constructor(payload: PublicExecutionQuotaPayload) {
    const quota = payload.execution_quota ?? {};
    const retryAfterSeconds = Number(
      payload.retry_after_seconds ?? quota.retry_after_seconds ?? 1200,
    );
    const retryAfterLabel = formatRetryAfterDuration(retryAfterSeconds);
    const maxRuns = quota.max_per_session;

    super(
      maxRuns
        ? `Demo limit reached. You can run up to ${maxRuns} workflows every ${retryAfterLabel}. Please wait before running another workflow.`
        : `Demo limit reached. Please wait about ${retryAfterLabel} before running another workflow.`,
    );

    this.name = 'PublicExecutionQuotaError';
    this.payload = payload;
    this.retryAfterSeconds = retryAfterSeconds;
    this.resetAt = payload.reset_at ?? quota.reset_at;
  }
}

export function isPublicExecutionQuotaPayload(payload: unknown): payload is PublicExecutionQuotaPayload {
  if (!payload || typeof payload !== 'object') return false;
  const candidate = payload as PublicExecutionQuotaPayload;
  return Boolean(candidate.execution_quota);
}

export function formatPublicExecutionQuotaMessage(error: unknown): string {
  if (error instanceof PublicExecutionQuotaError) return error.message;

  if (error && typeof error === 'object' && 'execution_quota' in error) {
    return new PublicExecutionQuotaError(error as PublicExecutionQuotaPayload).message;
  }

  return 'Demo limit reached. Please wait about 20 minutes before running another workflow.';
}

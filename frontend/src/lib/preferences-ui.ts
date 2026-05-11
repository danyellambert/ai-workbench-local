import type { ProviderConnection } from '@/types/settings';

import { formatUserDateTime } from '@/lib/user-time';
export const CONNECTION_ROLE_LABELS: Record<string, string> = {
  production: 'Production',
  benchmark_reference: 'Benchmark',
  burst_overflow: 'Burst / Overflow',
  local_dev: 'Local Dev',
  deep_review: 'Deep Review',
  long_context: 'Long Context',
};

export function formatPreferencesUpdatedAt(value?: string | number | null): string {
  return formatUserDateTime(value);
}

export function formatConnectionCheckedAt(value?: string | null): string {
  if (!value) return 'Never';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function credentialStatusCopy(connection: ProviderConnection): string {
  if (connection.authMethod === 'none') {
    return 'No API key is required for the local runtime path.';
  }
  if (connection.apiKeyConfigured) {
    if (connection.credentialManagement === 'macos_keychain') {
      return 'Credential stored in the deployment credential store and never returned to the frontend.';
    }
    return connection.credentialManagement === 'env_only'
      ? 'Credential configured outside the UI and managed via environment or secure external config.'
      : 'Credential configured for this connection.';
  }
  return connection.credentialManagement === 'macos_keychain'
    ? 'No credential stored yet. You can add it securely from this screen and it will be saved in the deployment credential store.'
    : 'Credentials are not configured in the current environment.';
}
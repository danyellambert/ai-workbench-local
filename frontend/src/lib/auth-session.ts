import { useQuery } from '@tanstack/react-query';

export type AuthIdentity = {
  role?: 'public' | 'admin' | string;
  can_write_global?: boolean;
  can_publish_external?: boolean;
};

export type AuthSession = {
  ok?: boolean;
  identity?: AuthIdentity;
  auth?: {
    admin_configured?: boolean;
    logged_out?: boolean;
  };
  error?: string;
};

export async function fetchAuthSession(): Promise<AuthSession> {
  const response = await fetch('/api/auth/session', {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error || 'Could not load auth session.');
  }
  return payload;
}

export function useAuthSession() {
  return useQuery({
    queryKey: ['auth-session'],
    queryFn: fetchAuthSession,
    refetchOnWindowFocus: false,
  });
}

export function isAdminSession(session?: AuthSession | null): boolean {
  return session?.identity?.role === 'admin';
}

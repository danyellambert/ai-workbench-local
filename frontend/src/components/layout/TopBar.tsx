import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, Command, Settings, Activity, ShieldCheck, Lock, LogOut, X } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { useLocation } from 'react-router-dom';
import { AI_LAB_ROUTE_MAP } from '@/lib/ai-lab-navigation';
import { getRuntimeControls } from '@/lib/product-api';
import { getRuntimeConnection } from '@/lib/runtime-controls-ui';

const routeTitles: Record<string, string> = {
  '/app': 'Command Center',
  '/app/documents': 'Document Library',
  '/app/run': 'Run Surface',
  '/app/workflows': 'Workflows',
  '/app/workflows/document-review': 'Document Review',
  '/app/workflows/comparison': 'Policy Comparison',
  '/app/workflows/action-plan': 'Action Plan',
  '/app/workflows/candidate-review': 'Candidate Review',
  '/app/deck-center': 'Deck Center',
  '/app/history': 'Run History',
  '/app/settings/runtime': 'Runtime Controls',
  '/app/settings/preferences': 'Preferences',
};

type AuthIdentity = {
  role?: 'public' | 'admin' | string;
  can_write_global?: boolean;
  can_publish_external?: boolean;
};

type AuthSession = {
  ok?: boolean;
  identity?: AuthIdentity;
  auth?: {
    admin_configured?: boolean;
    logged_out?: boolean;
  };
  error?: string;
};

async function fetchAuthSession(): Promise<AuthSession> {
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

async function loginAdmin(username: string, password: string): Promise<AuthSession> {
  const response = await fetch('/api/auth/admin/login', {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error || 'Admin login failed.');
  }
  return payload;
}

async function logoutAdmin(): Promise<AuthSession> {
  const response = await fetch('/api/auth/admin/logout', {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error || 'Admin logout failed.');
  }
  return payload;
}

export default function TopBar() {
  const { setCommandPaletteOpen, setRuntimeDrawerOpen } = useAppStore();
  const queryClient = useQueryClient();
  const location = useLocation();
  const [adminPanelOpen, setAdminPanelOpen] = useState(false);
  const [adminUsername, setAdminUsername] = useState('admin');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminActionPending, setAdminActionPending] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);

  const { data: runtimeControls, isLoading: runtimeControlsLoading, isError: runtimeControlsError } = useQuery({
    queryKey: ['runtime-controls'],
    queryFn: getRuntimeControls,
    refetchOnWindowFocus: false,
  });

  const { data: authSession } = useQuery({
    queryKey: ['auth-session'],
    queryFn: fetchAuthSession,
    refetchOnWindowFocus: false,
  });

  const labRoute = AI_LAB_ROUTE_MAP[location.pathname];
  const productTitle = routeTitles[location.pathname];
  const title = labRoute?.label || productTitle || 'Axiovance';
  const isLab = !!labRoute;
  const isSystem = !isLab && location.pathname.startsWith('/app/settings/');
  const isProduct = !isLab && !isSystem && !!productTitle;
  const sectionBadge = isLab ? 'AI Lab' : isSystem ? 'System' : isProduct ? 'Product' : null;
  const activeProfile = runtimeControls?.active_profile;
  const primaryConnection = activeProfile ? getRuntimeConnection(runtimeControls, activeProfile.primaryConnectionId) : undefined;
  const runtimeLabel = runtimeControlsLoading
    ? 'Loading runtime…'
    : runtimeControlsError || !activeProfile
      ? 'Runtime unavailable'
      : `${primaryConnection?.name ?? activeProfile.primaryConnectionId} · ${activeProfile.primaryModel}`;
  const isAdmin = authSession?.identity?.role === 'admin';
  const adminConfigured = authSession?.auth?.admin_configured !== false;

  const refreshAuthSession = async () => {
    await queryClient.invalidateQueries({ queryKey: ['auth-session'] });
    await queryClient.invalidateQueries({ queryKey: ['runtime-controls'] });
  };

  const handleAdminLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAdminActionPending(true);
    setAdminError(null);
    try {
      await loginAdmin(adminUsername, adminPassword);
      setAdminPassword('');
      setAdminPanelOpen(false);
      await refreshAuthSession();
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : 'Admin login failed.');
    } finally {
      setAdminActionPending(false);
    }
  };

  const handleAdminLogout = async () => {
    setAdminActionPending(true);
    setAdminError(null);
    try {
      await logoutAdmin();
      setAdminPassword('');
      setAdminPanelOpen(false);
      await refreshAuthSession();
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : 'Admin logout failed.');
    } finally {
      setAdminActionPending(false);
    }
  };

  return (
    <>
      <header className="h-14 border-b border-border/50 flex items-center justify-between px-6 bg-background/80 backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center gap-4">
          {sectionBadge && (
            <span className="text-[9px] uppercase tracking-widest text-primary/60 font-medium">
              {sectionBadge}
            </span>
          )}
          <h2 className="text-sm font-medium text-foreground">{title}</h2>
          <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-muted-foreground bg-secondary/50 px-2 py-1 rounded-md">
            <Activity className="w-3 h-3 text-glow-success" />
            <span>{runtimeLabel}</span>
          </div>
          <div className="hidden lg:flex items-center gap-1.5 text-[10px] text-muted-foreground bg-secondary/30 px-2 py-1 rounded-md">
            {isAdmin ? <ShieldCheck className="w-3 h-3 text-glow-success" /> : <Lock className="w-3 h-3" />}
            <span>{isAdmin ? 'Admin Mode' : 'Public Demo Mode'}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button onClick={() => setCommandPaletteOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border/50 bg-secondary/30 text-muted-foreground hover:text-foreground hover:bg-secondary/50 text-xs transition-colors">
            <Search className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Search or command...</span>
            <kbd className="hidden md:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-background rounded text-[10px] border border-border/50">
              <Command className="w-2.5 h-2.5" /> K
            </kbd>
          </button>
          <button onClick={() => setRuntimeDrawerOpen(true)}
            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
            aria-label="Open Runtime Controls">
            <Settings className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => {
              setAdminError(null);
              setAdminPanelOpen(true);
            }}
            className={`p-2 rounded-lg transition-colors ${
              isAdmin
                ? 'text-primary bg-primary/10 hover:bg-primary/15'
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
            }`}
            aria-label={isAdmin ? 'Open admin session panel' : 'Open admin login'}
            title={isAdmin ? 'Admin Mode' : 'Admin Login'}
          >
            {isAdmin ? <ShieldCheck className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {adminPanelOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 px-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-border/60 bg-card p-5 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] uppercase tracking-widest text-primary/70">
                  {isAdmin ? 'Admin Session' : 'Protected Access'}
                </p>
                <h3 className="mt-1 text-base font-semibold text-foreground">
                  {isAdmin ? 'Admin Mode is active' : 'Admin Login'}
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {isAdmin
                    ? 'You can manage global state, credentials, runtime controls, and external publishing.'
                    : 'Public visitors stay isolated in session overlays. Admin access unlocks global writes and publishing.'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAdminPanelOpen(false)}
                className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                aria-label="Close admin panel"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {!adminConfigured && (
              <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                Admin authentication is not configured in this environment.
              </div>
            )}

            {adminError && (
              <div className="mb-4 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                {adminError}
              </div>
            )}

            {isAdmin ? (
              <div className="space-y-3">
                <div className="rounded-xl border border-border/50 bg-secondary/30 p-3 text-xs text-muted-foreground">
                  Current role: <span className="font-medium text-foreground">admin</span>
                </div>
                <button
                  type="button"
                  onClick={handleAdminLogout}
                  disabled={adminActionPending}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-border/60 bg-secondary/40 px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary/70 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <LogOut className="h-4 w-4" />
                  {adminActionPending ? 'Signing out…' : 'Sign out of Admin Mode'}
                </button>
              </div>
            ) : (
              <form className="space-y-3" onSubmit={handleAdminLogin}>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-muted-foreground">Username</span>
                  <input
                    value={adminUsername}
                    onChange={(event) => setAdminUsername(event.target.value)}
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/60"
                    autoComplete="username"
                    disabled={adminActionPending}
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-muted-foreground">Password</span>
                  <input
                    value={adminPassword}
                    onChange={(event) => setAdminPassword(event.target.value)}
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/60"
                    type="password"
                    autoComplete="current-password"
                    disabled={adminActionPending}
                  />
                </label>
                <button
                  type="submit"
                  disabled={adminActionPending || !adminUsername.trim() || !adminPassword}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <ShieldCheck className="h-4 w-4" />
                  {adminActionPending ? 'Signing in…' : 'Enter Admin Mode'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

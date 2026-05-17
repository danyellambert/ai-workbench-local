import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Check,
  Cloud,
  Globe,
  HardDrive,
  Key,
  Layers,
  Link2,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { toast } from '@/components/ui/sonner';
import { GlassCard, MetricCard, PageHeader, StatusPill } from '@/components/shared/ui-components';
import AdminOnlyFeatureCard from '@/components/access/AdminOnlyFeatureCard';
import { isAdminSession, useAuthSession } from '@/lib/auth-session';
import {
  getPreferences,
  updatePreferencesConnectionCredential,
  testPreferencesConnection,
  updatePreferences,
  type PreferencesPatchPayload,
  type PreferencesResponse,
} from '@/lib/product-api';
import { CONNECTION_ROLE_LABELS, credentialStatusCopy, formatConnectionCheckedAt } from '@/lib/preferences-ui';
import { buildCatalogLookup } from '@/lib/runtime-controls-ui';
import type { ProviderConnection, RuntimeProfile } from '@/types/settings';

const CapabilityBadge = ({ label }: { label: string }) => (
  <span
    className="inline-flex items-center gap-1 rounded-full border border-glow-success/20 bg-glow-success/10 px-2 py-0.5 text-[9px] font-medium text-glow-success"
  >
    <Check className="h-2 w-2" />
    {label}
  </span>
);

const ModeIcon = ({ mode }: { mode: string }) => {
  if (mode === 'local') return <HardDrive className="h-4 w-4 text-primary" />;
  if (mode === 'hosted') return <Cloud className="h-4 w-4 text-accent" />;
  if (mode === 'openai-compatible') return <Globe className="h-4 w-4 text-glow-warning" />;
  return <Cloud className="h-4 w-4 text-glow-warning" />;
};

const ConnectionCard = ({
  connection,
  onTestConnection,
  isTesting,
  onSaveCredential,
  isSavingCredential,
}: {
  connection: ProviderConnection;
  onTestConnection: (connectionId: string) => void;
  isTesting: boolean;
  onSaveCredential: (connectionId: string, apiKey: string) => void;
  isSavingCredential: boolean;
}) => {
  const [credentialInput, setCredentialInput] = useState('');
  const caps = connection.capabilities;
  const credentialCopy = credentialStatusCopy(connection);
  const supportedCapabilities = [
    caps.generation ? 'Gen' : null,
    caps.embeddings ? 'Embed' : null,
    caps.structuredOutputs ? 'Structured' : null,
    caps.streaming ? 'Stream' : null,
    caps.vision ? 'Vision' : null,
    caps.toolCalling ? 'Tools' : null,
    caps.reranking ? 'Rerank' : null,
  ].filter(Boolean) as string[];
  const canEditCredential = connection.authMethod !== 'none' && connection.supportsCredentialUpdate;

  return (
    <GlassCard className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/40">
            <ModeIcon mode={connection.mode} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-medium text-foreground">{connection.name}</h4>
              <Badge variant="outline" className="border-border/60 px-1.5 py-0 text-[8px] text-muted-foreground">
                {CONNECTION_ROLE_LABELS[connection.role]}
              </Badge>
            </div>
            <p className="text-[10px] capitalize text-muted-foreground">{connection.mode} endpoint</p>
          </div>
        </div>
        <StatusPill status={connection.status} />
      </div>

      <p className="text-[10px] text-muted-foreground">{connection.description}</p>

      {supportedCapabilities.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {supportedCapabilities.map((label) => (
            <CapabilityBadge key={label} label={label} />
          ))}
        </div>
      ) : null}

      {connection.usageNote && (
        <p className="border-l-2 border-border pl-2 text-[10px] italic text-muted-foreground/80">{connection.usageNote}</p>
      )}

      <div className="space-y-2.5 rounded-xl border border-border/40 bg-secondary/10 p-3">
        <div className="space-y-1">
          <Label className="text-[10px] text-muted-foreground">Base URL</Label>
          <Input defaultValue={connection.baseUrl} className="h-8 bg-secondary/20 font-mono text-xs" readOnly />
        </div>

        {connection.authMethod !== 'none' ? (
          <div className="space-y-1">
            <Label className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Key className="h-3 w-3" />
              {connection.authMethod === 'bearer_token' ? 'Bearer Token' : 'API Key'}
            </Label>
            {canEditCredential ? (
              <>
                <Input
                  type="password"
                  value={credentialInput}
                  onChange={(event) => setCredentialInput(event.target.value)}
                  placeholder={connection.apiKeyConfigured ? 'Replace stored credential…' : 'Paste API key…'}
                  className="h-8 bg-secondary/20 font-mono text-xs"
                />
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="h-7 text-[10px]"
                    disabled={!credentialInput.trim() || isSavingCredential}
                    onClick={() => {
                      onSaveCredential(connection.id, credentialInput.trim());
                      setCredentialInput('');
                    }}
                  >
                    {isSavingCredential ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
                    Save key
                  </Button>
                  {connection.apiKeyConfigured ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-[10px] text-muted-foreground"
                      disabled={isSavingCredential}
                      onClick={() => onSaveCredential(connection.id, '')}
                    >
                      Clear
                    </Button>
                  ) : null}
                </div>
              </>
            ) : (
              <Input
                type="password"
                value={connection.apiKeyConfigured ? '••••••••••••••••' : ''}
                placeholder={connection.apiKeyConfigured ? '' : 'Not configured…'}
                className="h-8 bg-secondary/20 font-mono text-xs"
                readOnly
              />
            )}
            <p className={`text-[10px] ${connection.apiKeyConfigured ? 'text-glow-success' : 'text-muted-foreground italic'}`}>
              {credentialCopy}
            </p>
            {connection.credentialManagement === 'env_only' && (
              <p className="text-[10px] text-muted-foreground">Secrets are never returned to the frontend and remain managed outside the UI.</p>
            )}
          </div>
        ) : (
          <p className="text-[10px] italic text-muted-foreground">{credentialCopy}</p>
        )}

        <div className="space-y-1">
          <Label className="text-[10px] text-muted-foreground">Preferred Model</Label>
          <Input value={connection.preferredModel} className="h-8 bg-secondary/20 font-mono text-xs" readOnly />
        </div>
      </div>

      {connection.workflowFit && connection.workflowFit.length > 0 && (
        <div className="border-t border-border/50 pt-1">
          <p className="mb-1 text-[10px] text-muted-foreground">Workflow fit</p>
          <div className="flex flex-wrap gap-1">
            {connection.workflowFit.map((workflowId) => (
              <Badge key={workflowId} variant="outline" className="border-border/60 px-1.5 py-0 text-[8px] text-muted-foreground">
                {workflowId.replace(/-/g, ' ')}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {connection.lastErrorMessage && (
        <div className="rounded-lg border border-glow-warning/20 bg-glow-warning/5 p-2">
          <p className="text-[10px] text-glow-warning">Last error: {connection.lastErrorMessage}</p>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-border pt-1">
        <span className="text-[10px] text-muted-foreground">Last checked: {formatConnectionCheckedAt(connection.lastChecked)}</span>
        <Button variant="ghost" size="sm" className="h-7 text-[10px] text-muted-foreground hover:text-foreground" onClick={() => onTestConnection(connection.id)} disabled={isTesting}>
          {isTesting ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
          {isTesting ? 'Testing…' : 'Test connection'}
        </Button>
      </div>
    </GlassCard>
  );
};

const ProfileCard = ({
  profile,
  connection,
  executionPolicyLabel,
  qualityPostureLabel,
  docPresetLabel,
  onSetActive,
  disabled,
}: {
  profile: RuntimeProfile;
  connection?: ProviderConnection;
  executionPolicyLabel: string;
  qualityPostureLabel: string;
  docPresetLabel: string;
  onSetActive: (profileId: string) => void;
  disabled?: boolean;
}) => {

  return (
    <GlassCard className={profile.isActive ? 'border-primary/30 space-y-3' : 'space-y-3'}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-foreground">{profile.name}</span>
          {profile.isDefault && (
            <Badge variant="outline" className="border-primary/30 px-1.5 py-0 text-[9px] text-primary">
              Default
            </Badge>
          )}
          {profile.isActive && (
            <Badge variant="outline" className="border-glow-success/30 px-1.5 py-0 text-[9px] text-glow-success">
              Active
            </Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-[10px] text-muted-foreground hover:text-foreground"
          disabled={profile.isActive || disabled}
          onClick={() => onSetActive(profile.id)}
        >
          {profile.isActive ? 'Active' : 'Set active'}
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-xl border border-border/40 bg-secondary/10 p-3">
        <div>
          <p className="text-[10px] text-muted-foreground">Connection</p>
          <p className="text-[10px] text-foreground">{connection?.name ?? 'Unknown'}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Model</p>
          <p className="truncate text-[10px] font-mono text-foreground" title={profile.primaryModel}>{profile.primaryModel}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Execution Policy</p>
          <p className="text-[10px] text-foreground">{executionPolicyLabel}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Retrieval</p>
          <p className="text-[10px] capitalize text-foreground">{profile.retrievalStrategy}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Quality</p>
          <p className="text-[10px] text-foreground">{qualityPostureLabel}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Doc Preset</p>
          <p className="text-[10px] text-foreground">{docPresetLabel}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Max Output Tokens</p>
          <p className="text-[10px] font-mono text-foreground">{profile.generation.maxOutputTokens.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Temperature / Top-P</p>
          <p className="text-[10px] font-mono text-foreground">{profile.generation.temperature} / {profile.generation.topP}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Embedding</p>
          <p className="truncate text-[10px] font-mono text-foreground" title={profile.embeddingModel}>{profile.embeddingModel}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Top-K / Grounding</p>
          <p className="text-[10px] text-foreground">{profile.retrieval.topK} · {profile.retrieval.groundingStrictness}</p>
        </div>
      </div>

      {profile.fallbackChain.length > 0 && (
        <p className="text-[10px] text-muted-foreground">Fallback: {profile.fallbackChain.map((step) => step.label).join(' → ')}</p>
      )}

      <p className="text-[10px] italic text-muted-foreground">{profile.summary}</p>
    </GlassCard>
  );
};

export default function PreferencesPage() {
  const queryClient = useQueryClient();
  const [testingConnectionId, setTestingConnectionId] = useState<string | null>(null);
  const [savingCredentialConnectionId, setSavingCredentialConnectionId] = useState<string | null>(null);
  const [adminOnlyPreferencesCtaOpen, setAdminOnlyPreferencesCtaOpen] = useState(false);
  const { data: authSession } = useAuthSession();
  const isAdmin = isAdminSession(authSession);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['preferences'],
    queryFn: getPreferences,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  const [loadTimedOut, setLoadTimedOut] = useState(false);

  useEffect(() => {
    if (!isLoading || data) {
      setLoadTimedOut(false);
      return;
    }
    const timeout = window.setTimeout(() => setLoadTimedOut(true), 8000);
    return () => window.clearTimeout(timeout);
  }, [isLoading, data]);

  const saveMutation = useMutation({
    mutationFn: ({ payload }: { payload: PreferencesPatchPayload; successMessage: string }) => updatePreferences(payload),
    onSuccess: (response, variables) => {
      queryClient.setQueryData(['preferences'], response);
      queryClient.invalidateQueries({ queryKey: ['runtime-controls'] });
      toast.success(variables.successMessage);
    },
    onError: (mutationError) => {
      toast.error(mutationError instanceof Error ? mutationError.message : 'Failed to update preferences.');
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: (connectionId: string) => testPreferencesConnection(connectionId),
    onMutate: (connectionId) => {
      setTestingConnectionId(connectionId);
    },
    onSuccess: (response) => {
      queryClient.setQueryData<PreferencesResponse | undefined>(['preferences'], (current) => {
        if (!current) return current;
        return {
          ...current,
          provider_connections: current.provider_connections.map((connection) =>
            connection.id === response.connection_id
              ? {
                  ...connection,
                  status: response.result.status as ProviderConnection['status'],
                  lastChecked: response.result.checked_at,
                  ...(response.result.error_message ? { lastErrorMessage: response.result.error_message } : { lastErrorMessage: undefined }),
                }
              : connection,
          ),
        };
      });
      toast.success(`Connection test finished with status: ${response.result.status.replace('_', ' ')}`);
      setTestingConnectionId(null);
    },
    onError: (mutationError) => {
      toast.error(mutationError instanceof Error ? mutationError.message : 'Failed to test connection.');
      setTestingConnectionId(null);
    },
  });

  const credentialMutation = useMutation({
    mutationFn: ({ connectionId, apiKey }: { connectionId: string; apiKey: string }) => updatePreferencesConnectionCredential(connectionId, apiKey),
    onMutate: ({ connectionId }) => {
      setSavingCredentialConnectionId(connectionId);
    },
    onSuccess: (response) => {
      queryClient.setQueryData(['preferences'], response);
      queryClient.invalidateQueries({ queryKey: ['runtime-controls'] });
      toast.success('Connection credential updated securely.');
      setSavingCredentialConnectionId(null);
    },
    onError: (mutationError) => {
      toast.error(mutationError instanceof Error ? mutationError.message : 'Failed to update the connection credential.');
      setSavingCredentialConnectionId(null);
    },
  });

  const normalizedData = useMemo(() => {
    if (!data) return undefined;
    return {
      ...data,
      provider_connections: data.provider_connections ?? [],
      runtime_profiles: data.runtime_profiles ?? [],
      catalogs: data.catalogs ?? { executionPolicies: [], qualityPostures: [], docPresets: [] },
      credential_policy: data.credential_policy ?? { notes: [] },
    };
  }, [data]);

  const executionPolicyLookup = useMemo(() => buildCatalogLookup(normalizedData?.catalogs.executionPolicies), [normalizedData?.catalogs.executionPolicies]);
  const qualityPostureLookup = useMemo(() => buildCatalogLookup(normalizedData?.catalogs.qualityPostures), [normalizedData?.catalogs.qualityPostures]);
  const docPresetLookup = useMemo(() => buildCatalogLookup(normalizedData?.catalogs.docPresets), [normalizedData?.catalogs.docPresets]);
  const profiles = normalizedData?.runtime_profiles ?? [];
  const connectionsById = useMemo(
    () => Object.fromEntries((normalizedData?.provider_connections ?? []).map((connection) => [connection.id, connection] as const)),
    [normalizedData?.provider_connections],
  );
  const isBusy = saveMutation.isPending;

  const preferencesAdminOnlyCard = (
    <AdminOnlyFeatureCard
      eyebrow="Admin-only configuration"
      title="Provider credentials and workspace preferences are protected"
      description="The public demo never exposes or changes API keys, provider credentials, runtime profiles, or workspace-level preferences. These controls affect the whole Axiovance environment, so they require Admin Mode."
      valuePoints={[
        'Review provider metadata and runtime profile posture safely.',
        'Connect your own providers, keys, and workflow defaults in a guided demo.',
        'Keep the public demo stable while protecting credentials and global settings.',
      ]}
      secondaryLabel="Want to connect your own tools?"
      secondaryText="Connect with Danyel and we can walk through credentials, providers, runtime profiles, and operator preferences in a private workspace."
      compact
    />
  );

  const savePreferences = (payload: PreferencesPatchPayload, successMessage: string) => {
    if (!isAdmin) {
      setAdminOnlyPreferencesCtaOpen(true);
      return;
    }
    saveMutation.mutate({ payload, successMessage });
  };

  const handleSetActiveProfile = (profileId: string) => {
    savePreferences({ active_profile_id: profileId }, 'Active runtime profile updated.');
  };


  if (isLoading && !normalizedData && !loadTimedOut) {
    return (
      <motion.div className="mx-auto max-w-[920px] p-6 lg:p-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <PageHeader
          title="Preferences"
          description="Saved provider connections, runtime profiles, and operator preferences."
        >
          <Badge variant="outline" className="border-primary/30 text-[10px] text-primary">
            Loading live preferences
          </Badge>
        </PageHeader>
        <GlassCard>
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Loading preferences from the backend…</div>
              <div className="text-[10px] text-muted-foreground">This screen waits for the persisted workspace contract so it can render real connections and profiles.</div>
            </div>
            <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        </GlassCard>
      </motion.div>
    );
  }

  if (!normalizedData) {
    return (
      <motion.div className="mx-auto max-w-[920px] p-6 lg:p-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <PageHeader
          title="Preferences"
          description="Saved provider connections, runtime profiles, and operator preferences."
        />
        <GlassCard>
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs text-glow-warning">
              <AlertCircle className="h-4 w-4" />
              {loadTimedOut ? 'Preferences request timed out before the workspace contract became visible in the browser.' : error instanceof Error ? error.message : 'Preferences could not be loaded from the backend.'}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="h-8 text-[10px]" onClick={() => refetch()}>
                <RefreshCw className="mr-1 h-3 w-3" /> Retry
              </Button>
              <Button variant="ghost" size="sm" className="h-8 text-[10px] text-muted-foreground" onClick={() => window.location.assign('/app/settings/runtime')}>
                Open Runtime Controls
              </Button>
            </div>
          </div>
        </GlassCard>
      </motion.div>
    );
  }

  return (
    <motion.div className="mx-auto max-w-[920px] p-6 lg:p-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="preferences-header">
        <PageHeader
          title="Preferences"
          description="Saved provider connections, runtime profiles, and operator preferences."
        >
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-primary/30 text-[10px] text-primary">
            Live preferences
          </Badge>
          <Badge variant="outline" className="border-border/60 text-[10px] text-muted-foreground">
            {normalizedData.contract_version}
          </Badge>
          {isBusy && (
            <Badge variant="outline" className="border-border/60 text-[10px] text-muted-foreground">
              Saving…
            </Badge>
          )}
        </div>
        </PageHeader>
      </div>

      <div className="space-y-6">
        {adminOnlyPreferencesCtaOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/55 px-4 backdrop-blur-sm">
            <div className="w-full max-w-2xl">
              {preferencesAdminOnlyCard}
              <div className="mt-3 flex justify-end">
                <Button variant="ghost" size="sm" onClick={() => setAdminOnlyPreferencesCtaOpen(false)}>
                  Keep exploring the curated demo
                </Button>
              </div>
            </div>
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-3" data-tour="preferences-metrics">
          <MetricCard label="Connections" value={normalizedData.provider_connections.length} icon={Link2} delay={0.03} />
          <MetricCard label="Healthy" value={normalizedData.provider_connections.filter((connection) => connection.status === 'connected').length} icon={Check} glowColor="success" delay={0.06} />
          <MetricCard label="Saved profiles" value={profiles.length} icon={Layers} glowColor="accent" delay={0.09} />
        </div>

        <GlassCard data-tour="preferences-summary">
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Active profile</p>
              <p className="mt-1 text-sm font-medium text-foreground">{profiles.find((profile) => profile.isActive)?.name ?? 'No active profile'}</p>
              <p className="text-[10px] text-muted-foreground">Preferences persists profile defaults, connections and operator posture for the whole workspace.</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Protected writes</p>
              <p className="mt-1 text-sm font-medium text-foreground">{isAdmin ? 'Admin enabled' : 'Public demo locked'}</p>
              <p className="text-[10px] text-muted-foreground">Provider tests, credential updates, and profile changes are protected behind Admin Mode.</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Credential handling</p>
              <p className="mt-1 text-sm font-medium text-foreground">{(normalizedData.credential_policy as { mode?: string }).mode === 'workspace_managed' ? 'Workspace-managed' : 'Externally managed'}</p>
              <p className="text-[10px] text-muted-foreground">Secrets remain masked; only the management posture and connection health are shown here.</p>
            </div>
          </div>
        </GlassCard>
        {isError && (
          <GlassCard>
            <div className="flex items-center gap-2 text-xs text-glow-warning">
              <AlertCircle className="h-4 w-4" />
              {error instanceof Error ? error.message : 'Preferences loaded with backend caveats.'}
            </div>
          </GlassCard>
        )}

        <div data-tour="preferences-connections">
          <div className="mb-3 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-medium text-foreground">Provider Connections</h2>
          </div>
          <p className="mb-4 text-[10px] text-muted-foreground">
            Live provider connections are discovered from the backend runtime registry, with workspace-safe metadata overlays and connection tests.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {normalizedData.provider_connections.map((connection) => (
              <ConnectionCard
                key={connection.id}
                connection={connection}
                onTestConnection={(connectionId) => isAdmin ? testConnectionMutation.mutate(connectionId) : setAdminOnlyPreferencesCtaOpen(true)}
                isTesting={testingConnectionId === connection.id && testConnectionMutation.isPending}
                onSaveCredential={(connectionId, apiKey) => isAdmin ? credentialMutation.mutate({ connectionId, apiKey }) : setAdminOnlyPreferencesCtaOpen(true)}
                isSavingCredential={savingCredentialConnectionId === connection.id && credentialMutation.isPending}
              />
            ))}
          </div>
        </div>

        <Separator />

        <div data-tour="preferences-profiles">
          <div className="mb-3 flex items-center gap-2">
            <Layers className="h-4 w-4 text-accent" />
            <h2 className="text-sm font-medium text-foreground">Saved Runtime Profiles</h2>
          </div>
          <p className="mb-4 text-[10px] text-muted-foreground">
            Each saved profile resolves to a provider connection and the full execution stack: generation, retrieval, processing, fallback, and output budget.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {profiles.map((profile) => (
              <ProfileCard
                key={profile.id}
                profile={profile}
                connection={connectionsById[profile.primaryConnectionId]}
                executionPolicyLabel={executionPolicyLookup[profile.executionPolicy]?.label ?? profile.executionPolicy}
                qualityPostureLabel={qualityPostureLookup[profile.qualityPosture]?.label ?? profile.qualityPosture}
                docPresetLabel={docPresetLookup[profile.docProcessingPreset]?.label ?? profile.docProcessingPreset}
                onSetActive={handleSetActiveProfile}
                disabled={isBusy}
              />
            ))}
          </div>
        </div>

      </div>
    </motion.div>
  );
}
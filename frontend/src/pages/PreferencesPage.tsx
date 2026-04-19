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
  Settings2,
  Shield,
  User,
  WifiOff,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { toast } from '@/components/ui/sonner';
import { GlassCard, MetricCard, PageHeader, StatusPill } from '@/components/shared/ui-components';
import {
  getPreferences,
  updatePreferencesConnectionCredential,
  testPreferencesConnection,
  updatePreferences,
  type PreferencesPatchPayload,
  type PreferencesResponse,
} from '@/lib/product-api';
import { CONNECTION_ROLE_LABELS, credentialStatusCopy, formatConnectionCheckedAt, formatPreferencesUpdatedAt } from '@/lib/preferences-ui';
import { buildCatalogLookup } from '@/lib/runtime-controls-ui';
import type { ConnectionPolicyRule, OperatorPreferences, ProviderConnection, RuntimeProfile, WorkflowDefault, WorkflowFit } from '@/types/settings';

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

const CompatibilityBadge = ({ fit }: { fit: WorkflowFit }) => {
  const colors = {
    recommended: { bg: 'bg-glow-success/10', text: 'text-glow-success', border: 'border-glow-success/20' },
    compatible: { bg: 'bg-primary/10', text: 'text-primary', border: 'border-primary/20' },
    restricted: { bg: 'bg-glow-warning/10', text: 'text-glow-warning', border: 'border-glow-warning/20' },
    unsupported: { bg: 'bg-glow-error/10', text: 'text-glow-error', border: 'border-glow-error/20' },
  }[fit.compatibility] ?? { bg: 'bg-primary/10', text: 'text-primary', border: 'border-primary/20' };

  return (
    <span className={`inline-flex items-center rounded-full border px-1.5 py-0.5 text-[8px] font-medium capitalize ${colors.bg} ${colors.border} ${colors.text}`}>
      {fit.compatibility}
    </span>
  );
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
          <p className="truncate text-[10px] font-mono text-foreground">{profile.primaryModel}</p>
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
      </div>

      {profile.fallbackChain.length > 0 && (
        <p className="text-[10px] text-muted-foreground">Fallback: {profile.fallbackChain.map((step) => step.label).join(' → ')}</p>
      )}

      {profile.workflowFit.length > 0 ? (
        <div className="border-t border-border/50 pt-1.5">
          <p className="mb-1 text-[10px] text-muted-foreground">Workflow compatibility</p>
          <div className="space-y-1">
            {profile.workflowFit.map((fit) => (
              <div key={fit.workflowId} className="flex items-center gap-2">
                <span className="w-28 truncate text-[10px] text-foreground">{fit.label}</span>
                <CompatibilityBadge fit={fit} />
                {fit.reason && <span className="flex-1 truncate text-[9px] text-muted-foreground" title={fit.reason}>{fit.reason}</span>}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <p className="text-[10px] italic text-muted-foreground">{profile.summary}</p>
    </GlassCard>
  );
};

const PreferenceToggle = ({
  label,
  description,
  checked,
  onCheckedChange,
  disabled = false,
}: {
  label: string;
  description: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
}) => (
  <div className="flex items-center justify-between py-1.5">
    <div>
      <Label className="text-xs text-foreground">{label}</Label>
      <p className="text-[10px] text-muted-foreground">{description}</p>
    </div>
    <Switch checked={checked} onCheckedChange={onCheckedChange} disabled={disabled} />
  </div>
);

export default function PreferencesPage() {
  const queryClient = useQueryClient();
  const [testingConnectionId, setTestingConnectionId] = useState<string | null>(null);
  const [savingCredentialConnectionId, setSavingCredentialConnectionId] = useState<string | null>(null);

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
      workflow_defaults: data.workflow_defaults ?? [],
      connection_policy_rules: data.connection_policy_rules ?? [],
      catalogs: data.catalogs ?? { executionPolicies: [], qualityPostures: [], docPresets: [] },
      credential_policy: data.credential_policy ?? { notes: [] },
    };
  }, [data]);

  const executionPolicyLookup = useMemo(() => buildCatalogLookup(normalizedData?.catalogs.executionPolicies), [normalizedData?.catalogs.executionPolicies]);
  const qualityPostureLookup = useMemo(() => buildCatalogLookup(normalizedData?.catalogs.qualityPostures), [normalizedData?.catalogs.qualityPostures]);
  const docPresetLookup = useMemo(() => buildCatalogLookup(normalizedData?.catalogs.docPresets), [normalizedData?.catalogs.docPresets]);
  const profiles = normalizedData?.runtime_profiles ?? [];
  const workflowDefaults = normalizedData?.workflow_defaults ?? [];
  const operatorPreferences = normalizedData?.operator_preferences;
  const connectionsById = useMemo(
    () => Object.fromEntries((normalizedData?.provider_connections ?? []).map((connection) => [connection.id, connection] as const)),
    [normalizedData?.provider_connections],
  );
  const isBusy = saveMutation.isPending;

  const savePreferences = (payload: PreferencesPatchPayload, successMessage: string) => {
    saveMutation.mutate({ payload, successMessage });
  };

  const handleSetActiveProfile = (profileId: string) => {
    savePreferences({ active_profile_id: profileId }, 'Active runtime profile updated.');
  };

  const handleWorkflowDefaultChange = (workflowId: string, profileId: string) => {
    const nextDefaults: WorkflowDefault[] = workflowDefaults.map((item) =>
      item.workflowId === workflowId ? { ...item, profileId } : item,
    );
    savePreferences({ workflow_defaults: nextDefaults }, 'Workflow defaults updated.');
  };

  const handlePolicyRuleChange = (ruleId: string, enabled: boolean) => {
    const nextRules: ConnectionPolicyRule[] = (normalizedData?.connection_policy_rules ?? []).map((rule) =>
      rule.id === ruleId ? { ...rule, enabled } : rule,
    );
    savePreferences({ connection_policy_rules: nextRules }, 'Workspace policy updated.');
  };

  const handleOperatorPreferenceChange = (patch: Partial<OperatorPreferences>, successMessage: string) => {
    savePreferences({ operator_preferences: patch }, successMessage);
  };

  if (isLoading && !normalizedData && !loadTimedOut) {
    return (
      <motion.div className="mx-auto max-w-[920px] p-6 lg:p-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <PageHeader
          title="Preferences"
          description="Saved provider connections, runtime profiles, workflow defaults, and workspace policy."
        >
          <Badge variant="outline" className="border-primary/30 text-[10px] text-primary">
            Loading live preferences
          </Badge>
        </PageHeader>
        <GlassCard>
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Loading preferences from the backend…</div>
              <div className="text-[10px] text-muted-foreground">This screen waits for the persisted workspace contract so it can render real connections, profiles and defaults.</div>
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
          description="Saved provider connections, runtime profiles, workflow defaults, and workspace policy."
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
      <PageHeader
        title="Preferences"
        description="Saved provider connections, runtime profiles, workflow defaults, and workspace policy — now backed by live workspace configuration."
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

      <div className="space-y-6">
        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label="Connections" value={normalizedData.provider_connections.length} icon={Link2} delay={0.03} />
          <MetricCard label="Healthy" value={normalizedData.provider_connections.filter((connection) => connection.status === 'connected').length} icon={Check} glowColor="success" delay={0.06} />
          <MetricCard label="Saved profiles" value={profiles.length} icon={Layers} glowColor="accent" delay={0.09} />
          <MetricCard label="Workflow defaults" value={workflowDefaults.length} icon={Settings2} glowColor="warning" delay={0.12} />
        </div>

        <GlassCard>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Active profile</p>
              <p className="mt-1 text-sm font-medium text-foreground">{profiles.find((profile) => profile.isActive)?.name ?? 'No active profile'}</p>
              <p className="text-[10px] text-muted-foreground">Preferences persists profile defaults, connections and operator posture for the whole workspace.</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Default export</p>
              <p className="mt-1 text-sm font-medium text-foreground">{operatorPreferences?.defaultExportFormat?.toUpperCase?.() ?? 'n/a'}</p>
              <p className="text-[10px] text-muted-foreground">Runtime controls stay focused on the live route; Preferences stays focused on saved defaults.</p>
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

        <div>
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
                onTestConnection={(connectionId) => testConnectionMutation.mutate(connectionId)}
                isTesting={testingConnectionId === connection.id && testConnectionMutation.isPending}
                onSaveCredential={(connectionId, apiKey) => credentialMutation.mutate({ connectionId, apiKey })}
                isSavingCredential={savingCredentialConnectionId === connection.id && credentialMutation.isPending}
              />
            ))}
          </div>
        </div>

        <Separator />

        <div>
          <div className="mb-3 flex items-center gap-2">
            <Layers className="h-4 w-4 text-accent" />
            <h2 className="text-sm font-medium text-foreground">Saved Runtime Profiles</h2>
          </div>
          <p className="mb-4 text-[10px] text-muted-foreground">
            Each saved profile resolves to a provider connection and the full execution stack: generation, retrieval, processing, fallback, and policy.
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

        <Separator />

        <GlassCard>
          <div className="mb-3 flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Workflow Defaults</h3>
          </div>
          <p className="mb-3 text-[10px] text-muted-foreground">
            Workflows bind to runtime profiles rather than raw models so that routing, retrieval, and document processing stay coherent.
          </p>
          <div className="space-y-1">
            {workflowDefaults.map((workflowDefault) => {
              const profile = profiles.find((item) => item.id === workflowDefault.profileId);
              const connection = profile ? connectionsById[profile.primaryConnectionId] : undefined;

              return (
                <div key={workflowDefault.workflowId} className="flex items-center justify-between gap-3 py-1.5">
                  <div className="min-w-0 flex-1">
                    <span className="text-xs text-foreground">{workflowDefault.label}</span>
                    {connection && <p className="text-[9px] text-muted-foreground">via {connection.name}</p>}
                  </div>
                  <Select value={workflowDefault.profileId} onValueChange={(value) => handleWorkflowDefaultChange(workflowDefault.workflowId, value)}>
                    <SelectTrigger className="h-7 w-[210px] bg-secondary/20 text-[10px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {profiles.map((profileOption) => (
                        <SelectItem key={profileOption.id} value={profileOption.id} className="text-xs">
                          {profileOption.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              );
            })}
          </div>
        </GlassCard>

        <GlassCard>
          <div className="mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Workspace Policy</h3>
          </div>
          <p className="mb-3 text-[10px] text-muted-foreground">
            Workspace-level policy expresses what this workspace allows by default. Live runtime routing and diagnostics stay in Runtime Controls.
          </p>
          <div className="space-y-2">
            {normalizedData.connection_policy_rules.map((rule) => (
              <div key={rule.id} className="flex items-center justify-between gap-4 rounded-lg border border-border/40 bg-secondary/10 px-3 py-2.5">
                <div className="flex-1">
                  <Label className="text-xs text-foreground">{rule.label}</Label>
                  <p className="text-[10px] text-muted-foreground">{rule.description}</p>
                </div>
                <Switch checked={rule.enabled} disabled={isBusy} onCheckedChange={(checked) => handlePolicyRuleChange(rule.id, checked)} />
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard>
          <div className="mb-3 flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-medium text-foreground">Operator Preferences</h3>
          </div>
          {operatorPreferences ? (
          <div className="space-y-1">
            <PreferenceToggle
              label="Show Source Badges"
              description="Display provenance badges on findings and outputs."
              checked={operatorPreferences.showSourceBadges}
              disabled={isBusy}
              onCheckedChange={(checked) => handleOperatorPreferenceChange({ showSourceBadges: checked }, 'Operator preference updated.')}
            />

            <div className="flex items-center justify-between py-1.5">
              <div>
                <Label className="text-xs text-foreground">Default Export Format</Label>
                <p className="text-[10px] text-muted-foreground">Used for deck and report exports.</p>
              </div>
              <Select value={operatorPreferences.defaultExportFormat} onValueChange={(value) => handleOperatorPreferenceChange({ defaultExportFormat: value as OperatorPreferences['defaultExportFormat'] }, 'Default export format updated.')}>
                <SelectTrigger className="h-7 w-[120px] bg-secondary/20 text-[10px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pptx">PowerPoint (.pptx)</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="markdown">Markdown</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between py-1.5">
              <div>
                <Label className="text-xs text-foreground">Benchmark Baseline</Label>
                <p className="text-[10px] text-muted-foreground">Default comparison profile for eval and benchmark views.</p>
              </div>
              <Select value={operatorPreferences.defaultBenchmarkBaseline} onValueChange={(value) => handleOperatorPreferenceChange({ defaultBenchmarkBaseline: value }, 'Benchmark baseline updated.')}>
                <SelectTrigger className="h-7 w-[220px] bg-secondary/20 text-[10px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {profiles.map((profile) => (
                    <SelectItem key={profile.id} value={profile.id} className="text-xs">
                      {profile.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          ) : null}
        </GlassCard>

        <div className="rounded-xl border border-border/40 bg-secondary/10 px-4 py-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 text-muted-foreground" />
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground">
                Preferences are now backed by a live workspace contract. Active runtime profile changes are synchronized with Runtime Controls.
              </p>
              <p className="text-[10px] text-muted-foreground">Last updated: {formatPreferencesUpdatedAt(normalizedData.updated_at)}</p>
              {(normalizedData.credential_policy.notes || []).map((note) => (
                <p key={note} className="text-[10px] text-muted-foreground">• {note}</p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
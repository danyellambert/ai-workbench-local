import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight,
  AlertTriangle,
  Check,
  ChevronRight,
  Cpu,
  FileText,
  Layers,
  RefreshCw,
  Search,
  Server,
  Shield,
  X,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { toast } from '@/components/ui/sonner';
import { GlassCard, PageHeader, StatusPill } from '@/components/shared/ui-components';
import {
  getRuntimeControls,
  updateRuntimeControls,
  type RuntimeControlsCatalogItem,
  type RuntimeControlsResponse,
} from '@/lib/product-api';
import {
  buildCatalogLookup,
  cloneRuntimeProfile,
  deriveRuntimeFallbackChain,
  deriveRuntimeWorkflowFit,
  EMPTY_PROVIDER_CAPABILITIES,
  formatRuntimeUpdatedAt,
  getRuntimeConnection,
  RUNTIME_COMPATIBILITY_COLORS,
} from '@/lib/runtime-controls-ui';
import type { RuntimeProfile, WorkflowFit } from '@/types/settings';

const Control = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="space-y-1.5">
    <Label className="text-xs text-muted-foreground">{label}</Label>
    {children}
  </div>
);

const ToggleRow = ({
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
  <div className="col-span-full flex items-center justify-between rounded-lg border border-border/40 bg-secondary/15 px-3 py-2.5">
    <div>
      <Label className="text-xs text-foreground">{label}</Label>
      <p className="text-[10px] text-muted-foreground">{description}</p>
    </div>
    <Switch checked={checked} onCheckedChange={onCheckedChange} disabled={disabled} />
  </div>
);

const CapabilityBadge = ({ label }: { label: string }) => (
  <span
    className="inline-flex items-center gap-1 rounded-full border border-glow-success/20 bg-glow-success/10 px-2 py-0.5 text-[10px] font-medium text-glow-success"
  >
    <Check className="h-2.5 w-2.5" />
    {label}
  </span>
);

const WorkflowFitBadge = ({ fit }: { fit: WorkflowFit }) => {
  const colors = RUNTIME_COMPATIBILITY_COLORS[fit.compatibility] ?? RUNTIME_COMPATIBILITY_COLORS.compatible;
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 ${colors.bg} ${colors.border}`}>
      <span className={`text-[10px] font-medium ${colors.text}`}>{fit.label}</span>
      <Badge variant="outline" className={`px-1.5 py-0 text-[8px] capitalize ${colors.border} ${colors.text}`}>
        {fit.compatibility}
      </Badge>
    </div>
  );
};

const DiagnosticItem = ({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description?: string;
}) => (
  <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
    <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
    <p className="mt-1 text-xs font-medium text-foreground">{value}</p>
    {description ? <p className="mt-1 text-[10px] text-muted-foreground">{description}</p> : null}
  </div>
);

function buildSelectLookup(items: RuntimeControlsCatalogItem[] | undefined): Record<string, RuntimeControlsCatalogItem> {
  return buildCatalogLookup(items);
}

export default function RuntimeControlsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['runtime-controls'],
    queryFn: getRuntimeControls,
    refetchOnWindowFocus: false,
  });

  const [draft, setDraft] = useState<RuntimeProfile | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (!data?.active_profile) return;
    if (!draft || !isDirty) {
      setDraft(cloneRuntimeProfile(data.active_profile));
      setIsDirty(false);
    }
  }, [data, draft, isDirty]);

  const saveMutation = useMutation({
    mutationFn: (profile: RuntimeProfile) => updateRuntimeControls({ profile }),
    onSuccess: (response) => {
      queryClient.setQueryData(['runtime-controls'], response);
      setDraft(cloneRuntimeProfile(response.active_profile));
      setIsDirty(false);
      toast.success('Runtime controls saved.');
    },
    onError: (mutationError) => {
      toast.error(mutationError instanceof Error ? mutationError.message : 'Failed to save runtime controls.');
    },
  });

  const profile = draft ?? data?.active_profile ?? null;

  const executionPolicyLookup = useMemo(() => buildSelectLookup(data?.catalogs.executionPolicies), [data?.catalogs.executionPolicies]);
  const qualityPostureLookup = useMemo(() => buildSelectLookup(data?.catalogs.qualityPostures), [data?.catalogs.qualityPostures]);
  const docPresetLookup = useMemo(() => buildSelectLookup(data?.catalogs.docPresets), [data?.catalogs.docPresets]);

  const primaryConnection = profile ? getRuntimeConnection(data, profile.primaryConnectionId) : undefined;
  const embeddingConnection = profile ? getRuntimeConnection(data, profile.embeddingConnectionId) : undefined;
  const capabilities = primaryConnection?.capabilities ?? EMPTY_PROVIDER_CAPABILITIES;
  const fallbackChain = profile ? deriveRuntimeFallbackChain(profile, data) : [];
  const workflowFit = profile ? deriveRuntimeWorkflowFit(profile, primaryConnection) : [];
  const supportedCapabilities = [
    capabilities.generation ? 'Generation' : null,
    capabilities.embeddings ? 'Embeddings' : null,
    capabilities.structuredOutputs ? 'Structured Outputs' : null,
    capabilities.streaming ? 'Streaming' : null,
    capabilities.vision ? 'Vision / VLM' : null,
    capabilities.toolCalling ? 'Tool Calling' : null,
    capabilities.reranking ? 'Reranking' : null,
  ].filter(Boolean) as string[];

  const updateProfile = (updater: (current: RuntimeProfile) => RuntimeProfile) => {
    setDraft((current) => {
      if (!current) return current;
      return updater(current);
    });
    setIsDirty(true);
  };

  const handlePrimaryConnectionChange = (connectionId: string) => {
    updateProfile((current) => {
      const modelOptions = (data?.options.modelsByConnection[connectionId] || []).filter(Boolean);
      const nextModel = modelOptions.includes(current.primaryModel) ? current.primaryModel : (modelOptions[0] || current.primaryModel);
      return {
        ...current,
        primaryConnectionId: connectionId,
        primaryModel: nextModel,
      };
    });
  };

  const handleEmbeddingConnectionChange = (connectionId: string) => {
    updateProfile((current) => {
      const modelOptions = (data?.options.embeddingModelsByConnection[connectionId] || []).filter(Boolean);
      const nextModel = modelOptions.includes(current.embeddingModel) ? current.embeddingModel : (modelOptions[0] || current.embeddingModel);
      return {
        ...current,
        embeddingConnectionId: connectionId,
        embeddingModel: nextModel,
      };
    });
  };

  const handleReset = () => {
    if (!data?.active_profile) return;
    setDraft(cloneRuntimeProfile(data.active_profile));
    setIsDirty(false);
  };

  if (isLoading && !profile) {
    return (
      <motion.div className="mx-auto max-w-[920px] p-6 lg:p-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <PageHeader
          title="Runtime Controls"
          description="Active execution configuration for the current system profile — generation, retrieval, routing, and document processing."
        >
          <Badge variant="outline" className="border-primary/30 text-[10px] text-primary">
            Loading live runtime
          </Badge>
        </PageHeader>
        <GlassCard>
          <div className="text-xs text-muted-foreground">Loading runtime controls from the backend…</div>
        </GlassCard>
      </motion.div>
    );
  }

  if (!profile) {
    return (
      <motion.div className="mx-auto max-w-[920px] p-6 lg:p-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <PageHeader
          title="Runtime Controls"
          description="Active execution configuration for the current system profile — generation, retrieval, routing, and document processing."
        />
        <GlassCard>
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="h-4 w-4" />
            {error instanceof Error ? error.message : 'Runtime controls could not be loaded from the backend.'}
          </div>
        </GlassCard>
      </motion.div>
    );
  }

  return (
    <motion.div className="mx-auto max-w-[920px] p-6 lg:p-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader
        title="Runtime Controls"
        description="Edit the currently active runtime profile. Workspace defaults and the saved profile library live in Preferences, while this screen focuses on the active execution path."
      >
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-primary/30 text-[10px] text-primary">
            Live runtime
          </Badge>
          <Badge variant="outline" className="border-border/60 text-[10px] text-muted-foreground">
            {data?.contract_version || 'runtime_controls.v1'}
          </Badge>
        </div>
      </PageHeader>

      <div className="space-y-6">
        {isError && (
          <GlassCard>
            <div className="flex items-center gap-2 text-xs text-glow-warning">
              <AlertTriangle className="h-4 w-4" />
              {error instanceof Error ? error.message : 'Runtime Controls loaded with backend caveats.'}
            </div>
          </GlassCard>
        )}

        <GlassCard>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Active Runtime Summary</h3>
              <StatusPill status="active" />
              {profile.isDefault && (
                <Badge variant="outline" className="border-primary/30 px-1.5 py-0 text-[9px] text-primary">
                  Default
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" className="h-8 text-xs" onClick={handleReset} disabled={!isDirty || saveMutation.isPending}>
                Reset
              </Button>
              <Button className="h-8 text-xs" onClick={() => saveMutation.mutate(profile)} disabled={!isDirty || saveMutation.isPending}>
                {saveMutation.isPending ? 'Saving…' : 'Save changes'}
              </Button>
            </div>
          </div>

          <div className="rounded-xl border border-border/50 bg-secondary/15 p-4">
            <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Profile</p>
                <p className="mt-0.5 text-sm font-medium text-foreground">{profile.name}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Provider Connection</p>
                <p className="mt-0.5 text-sm text-foreground">{primaryConnection?.name ?? 'Unknown'}</p>
                <p className="text-[10px] capitalize text-muted-foreground">
                  {primaryConnection?.mode ?? 'unknown'} · {primaryConnection?.status ?? 'unknown'}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Model</p>
                <p className="mt-0.5 text-xs font-mono text-foreground">{profile.primaryModel}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Embedding Stack</p>
                <p className="mt-0.5 text-sm text-foreground">{embeddingConnection?.name ?? 'Unknown'}</p>
                <p className="text-[10px] font-mono text-muted-foreground">{profile.embeddingModel}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Retrieval Strategy</p>
                <p className="mt-0.5 text-sm capitalize text-foreground">{profile.retrievalStrategy}</p>
                <p className="text-[10px] text-muted-foreground">Reranking {profile.rerankingEnabled ? 'enabled' : 'disabled'}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Document Processing</p>
                <p className="mt-0.5 text-sm text-foreground">{docPresetLookup[profile.docProcessingPreset]?.label ?? profile.docProcessingPreset}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Execution Policy</p>
                <p className="mt-0.5 text-sm text-foreground">{executionPolicyLookup[profile.executionPolicy]?.label ?? profile.executionPolicy}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Quality Posture</p>
                <p className="mt-0.5 text-sm text-foreground">{qualityPostureLookup[profile.qualityPosture]?.label ?? profile.qualityPosture}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Fallback Chain</p>
                <p className="mt-0.5 text-sm text-foreground">
                  {fallbackChain.length > 0 ? `${fallbackChain.length} step${fallbackChain.length > 1 ? 's' : ''}` : 'None — fail hard'}
                </p>
              </div>
            </div>
            <div className="mt-4 border-t border-border/50 pt-3">
              <p className="text-[10px] italic text-muted-foreground">{profile.summary}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">Last updated: {formatRuntimeUpdatedAt(data?.updated_at)}</p>
            </div>
          </div>
        </GlassCard>

        <div className="px-1">
          <div className="mb-1 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Active Controls</h3>
            <Badge variant="outline" className="border-primary/30 text-[9px] text-primary">
              Runtime-affecting
            </Badge>
          </div>
          <p className="text-[10px] text-muted-foreground">
            These controls are persisted and affect the real runtime path. They also synchronize back to the active saved profile shown in Preferences.
          </p>
        </div>

        <GlassCard>
          <div className="mb-1 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Generation</h3>
            <Badge variant="outline" className="border-primary/30 text-[9px] text-primary">
              Editable
            </Badge>
          </div>
          <p className="mb-4 text-[10px] text-muted-foreground">
            Resolved from profile <span className="font-medium text-foreground">{profile.name}</span>.
          </p>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Control label="Provider Connection">
              <Select value={profile.primaryConnectionId} onValueChange={handlePrimaryConnectionChange}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(data?.available_connections || []).map((connection) => (
                    <SelectItem key={connection.id} value={connection.id}>{connection.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

            <Control label="Model">
              <Select value={profile.primaryModel} onValueChange={(value) => updateProfile((current) => ({ ...current, primaryModel: value }))}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {((data?.options.modelsByConnection[profile.primaryConnectionId] || []).filter(Boolean)).map((model) => (
                    <SelectItem key={model} value={model}>{model}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

            <Control label="Context Window">
              <Select value={profile.generation.contextWindow} onValueChange={(value) => updateProfile((current) => ({ ...current, generation: { ...current.generation, contextWindow: value } }))}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(data?.catalogs.contextWindows || []).map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

            <Control label={`Temperature — ${profile.generation.temperature}`}>
              <Slider value={[profile.generation.temperature]} onValueChange={([value]) => updateProfile((current) => ({ ...current, generation: { ...current.generation, temperature: value } }))} min={0} max={1.5} step={0.05} className="py-2" />
            </Control>

            <Control label={`Top-P — ${profile.generation.topP}`}>
              <Slider value={[profile.generation.topP]} onValueChange={([value]) => updateProfile((current) => ({ ...current, generation: { ...current.generation, topP: value } }))} min={0} max={1} step={0.05} className="py-2" />
            </Control>

            <Control label={`Max Output Tokens — ${profile.generation.maxOutputTokens}`}>
              <Slider value={[profile.generation.maxOutputTokens]} onValueChange={([value]) => updateProfile((current) => ({ ...current, generation: { ...current.generation, maxOutputTokens: value } }))} min={256} max={16384} step={256} className="py-2" />
            </Control>

            <Control label="Prompt Profile">
              <Select value={profile.generation.promptProfile} onValueChange={(value) => updateProfile((current) => ({ ...current, generation: { ...current.generation, promptProfile: value } }))}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(data?.catalogs.promptProfiles || []).map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

          </div>
        </GlassCard>

        <GlassCard>
          <div className="mb-1 flex items-center gap-2">
            <Search className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-medium text-foreground">Retrieval & Ranking</h3>
            <Badge variant="outline" className="border-primary/30 text-[9px] text-primary">
              Editable
            </Badge>
          </div>
          <p className="mb-4 text-[10px] text-muted-foreground">
            Retrieval resolves through <span className="font-medium text-foreground">{embeddingConnection?.name ?? 'Unknown'}</span> using{' '}
            <span className="font-mono text-foreground">{profile.embeddingModel}</span>.
          </p>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Control label="Embedding Connection">
              <Select value={profile.embeddingConnectionId} onValueChange={handleEmbeddingConnectionChange}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(data?.available_connections || []).filter((connection) => connection.capabilities.embeddings).map((connection) => (
                    <SelectItem key={connection.id} value={connection.id}>{connection.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

            <Control label="Embedding Model">
              <Select value={profile.embeddingModel} onValueChange={(value) => updateProfile((current) => ({ ...current, embeddingModel: value }))}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {((data?.options.embeddingModelsByConnection[profile.embeddingConnectionId] || []).filter(Boolean)).map((model) => (
                    <SelectItem key={model} value={model}>{model}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

            <Control label={`Top-K — ${profile.retrieval.topK}`}>
              <Slider value={[profile.retrieval.topK]} onValueChange={([value]) => updateProfile((current) => ({ ...current, retrieval: { ...current.retrieval, topK: value } }))} min={1} max={50} step={1} className="py-2" />
            </Control>

            <Control label={`Chunk Size — ${profile.retrieval.chunkSize}`}>
              <Slider value={[profile.retrieval.chunkSize]} onValueChange={([value]) => updateProfile((current) => ({ ...current, retrieval: { ...current.retrieval, chunkSize: value } }))} min={256} max={4096} step={64} className="py-2" />
            </Control>

            <Control label={`Chunk Overlap — ${profile.retrieval.chunkOverlap}`}>
              <Slider value={[profile.retrieval.chunkOverlap]} onValueChange={([value]) => updateProfile((current) => ({ ...current, retrieval: { ...current.retrieval, chunkOverlap: value } }))} min={0} max={512} step={32} className="py-2" />
            </Control>

            <Control label={`Rerank Pool Size — ${profile.retrieval.rerankPoolSize}`}>
              <Slider value={[profile.retrieval.rerankPoolSize]} onValueChange={([value]) => updateProfile((current) => ({ ...current, retrieval: { ...current.retrieval, rerankPoolSize: value } }))} min={0} max={200} step={5} className="py-2" />
            </Control>

            <Control label={`Rerank Lexical Weight — ${profile.retrieval.rerankLexicalWeight}`}>
              <Slider value={[profile.retrieval.rerankLexicalWeight]} onValueChange={([value]) => updateProfile((current) => ({ ...current, retrieval: { ...current.retrieval, rerankLexicalWeight: value } }))} min={0} max={1} step={0.05} className="py-2" />
            </Control>

            <ToggleRow label="Reranker" description="Enable reranking after initial retrieval to improve ordering." checked={profile.rerankingEnabled} onCheckedChange={(checked) => updateProfile((current) => ({ ...current, rerankingEnabled: checked, retrieval: { ...current.retrieval, rerankPoolSize: checked ? Math.max(current.retrieval.rerankPoolSize, 10) : 0 } }))} />
          </div>
        </GlassCard>

        <GlassCard>
          <div className="mb-1 flex items-center gap-2">
            <FileText className="h-4 w-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Document Processing</h3>
            <Badge variant="outline" className="border-primary/30 text-[9px] text-primary">
              Editable
            </Badge>
          </div>
          <p className="mb-4 text-[10px] text-muted-foreground">
            Preset: <span className="font-medium text-foreground">{docPresetLookup[profile.docProcessingPreset]?.label ?? profile.docProcessingPreset}</span>
          </p>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Control label="PDF Extraction Mode">
              <Select value={profile.docProcessing.pdfExtractionMode} onValueChange={(value) => updateProfile((current) => ({ ...current, docProcessing: { ...current.docProcessing, pdfExtractionMode: value } }))}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(data?.catalogs.pdfExtractionModes || []).map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

            <Control label="OCR Backend">
              <Select value={profile.docProcessing.ocrBackend} onValueChange={(value) => updateProfile((current) => ({ ...current, docProcessing: { ...current.docProcessing, ocrBackend: value } }))}>
                <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(data?.catalogs.ocrBackends || []).map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Control>

            <Control label={`Scanned Doc Threshold — ${profile.docProcessing.scannedDocumentThreshold}`}>
              <Slider value={[profile.docProcessing.scannedDocumentThreshold]} onValueChange={([value]) => updateProfile((current) => ({ ...current, docProcessing: { ...current.docProcessing, scannedDocumentThreshold: value } }))} min={0.1} max={1} step={0.05} className="py-2" />
            </Control>

            <ToggleRow label="VLM Enhancement" description="Use a vision-language model for complex layouts when the profile enables it." checked={profile.docProcessing.vlmEnhancement} onCheckedChange={(checked) => updateProfile((current) => ({ ...current, docProcessing: { ...current.docProcessing, vlmEnhancement: checked } }))} />
            <ToggleRow label="OCR Failover" description="Fallback to OCR when extraction confidence drops below the configured threshold." checked={profile.docProcessing.ocrFailoverEnabled} onCheckedChange={(checked) => updateProfile((current) => ({ ...current, docProcessing: { ...current.docProcessing, ocrFailoverEnabled: checked } }))} />
          </div>
        </GlassCard>

        <div className="px-1 pt-1">
          <div className="mb-1 flex items-center gap-2">
            <Shield className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-medium text-foreground">Runtime Diagnostics</h3>
            <Badge variant="outline" className="border-border/60 text-[9px] text-muted-foreground">
              Read-only / demo layer
            </Badge>
          </div>
          <p className="text-[10px] text-muted-foreground">
            These blocks remain visible for explainability and AI engineer demos. They help inspect capability, compatibility, routing and derived policy signals without pretending every item is a first-class runtime knob.
          </p>
        </div>

        <GlassCard>
          <div className="mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-medium text-foreground">Policy & Derived Signals</h3>
            <Badge variant="outline" className="border-border/60 text-[9px] text-muted-foreground">
              Derived
            </Badge>
          </div>
          <p className="mb-3 text-[10px] text-muted-foreground">
            Useful for governance and demo narratives, but not currently treated as the primary control loop for runtime execution.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            <DiagnosticItem
              label="Execution Policy"
              value={executionPolicyLookup[profile.executionPolicy]?.label ?? profile.executionPolicy}
              description={executionPolicyLookup[profile.executionPolicy]?.description}
            />
            <DiagnosticItem
              label="Quality Posture"
              value={qualityPostureLookup[profile.qualityPosture]?.label ?? profile.qualityPosture}
              description="Currently more useful as an explainability signal than as a hard routing control."
            />
            <DiagnosticItem
              label="Retrieval Strategy"
              value={profile.retrievalStrategy}
              description="The current runtime behaves essentially as hybrid retrieval, so this is shown as a diagnostic signal rather than a key control." 
            />
            <DiagnosticItem
              label="Doc Processing Preset"
              value={docPresetLookup[profile.docProcessingPreset]?.label ?? profile.docProcessingPreset}
              description="Derived from the lower-level document processing settings kept in the active controls area."
            />
          </div>
        </GlassCard>

        <GlassCard>
          <div className="mb-3 flex items-center gap-2">
            <Server className="h-4 w-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Provider Capability Fit</h3>
            <Badge variant="outline" className="border-border/60 text-[9px] text-muted-foreground">
              Diagnostic
            </Badge>
          </div>
          <p className="mb-3 text-[10px] text-muted-foreground">
            Active generation provider: {primaryConnection?.name ?? 'Unknown'}. These capabilities shape what the runtime can safely do.
          </p>
          {supportedCapabilities.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {supportedCapabilities.map((label) => (
                <CapabilityBadge key={label} label={label} />
              ))}
            </div>
          ) : (
            <div className="mt-2 rounded-lg border border-border/40 bg-secondary/10 p-2.5">
              <p className="text-[10px] text-muted-foreground">No capability badge is shown here unless the backend can positively confirm it.</p>
            </div>
          )}
        </GlassCard>

        {workflowFit.length > 0 ? (
          <GlassCard>
            <div className="mb-3 flex items-center gap-2">
              <ArrowRight className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Workflow Compatibility</h3>
              <Badge variant="outline" className="border-border/60 text-[9px] text-muted-foreground">
                Verified only
              </Badge>
            </div>
            <p className="mb-3 text-[10px] text-muted-foreground">
              Only benchmark-backed or otherwise explicitly verified compatibility signals are shown here.
            </p>
            <div className="space-y-2">
              {workflowFit.map((fit) => (
                <div key={fit.workflowId} className="flex items-center justify-between gap-3 rounded-lg border border-border/40 bg-secondary/10 px-3 py-2">
                  <WorkflowFitBadge fit={fit} />
                  {fit.reason && (
                    <p className="max-w-[52%] truncate text-right text-[10px] text-muted-foreground" title={fit.reason}>
                      {fit.reason}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </GlassCard>
        ) : null}

        <GlassCard>
          <div className="mb-3 flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Fallback / Routing Chain</h3>
            <Badge variant="outline" className="border-border/60 text-[9px] text-muted-foreground">
              Diagnostic
            </Badge>
          </div>
          <p className="mb-3 text-[10px] text-muted-foreground">Ordered routing resolved from the active runtime profile.</p>
          <div className="space-y-0">
            <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
              <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/20 text-[9px] font-bold text-primary">1</div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-foreground">Primary — {primaryConnection?.name ?? 'Unknown'}</p>
                <p className="truncate text-[10px] font-mono text-muted-foreground">{profile.primaryModel}</p>
              </div>
              <StatusPill status={primaryConnection?.status ?? 'not_configured'} />
            </div>

            {fallbackChain.map((step, index) => {
              const fallbackConnection = getRuntimeConnection(data, step.connectionId);
              return (
                <div key={`${step.connectionId}-${index}`}>
                  <div className="flex justify-center py-1">
                    <ChevronRight className="h-3 w-3 rotate-90 text-muted-foreground" />
                  </div>
                  <div className="flex items-center gap-3 rounded-lg border border-border/50 bg-secondary/10 p-3">
                    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-secondary/60 text-[9px] font-bold text-muted-foreground">
                      {index + 2}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-foreground">{step.label}</p>
                      <p className="truncate text-[10px] font-mono text-muted-foreground">
                        {fallbackConnection?.name ?? step.connectionId} · {step.model}
                      </p>
                    </div>
                    <StatusPill status={fallbackConnection?.status ?? 'not_configured'} />
                  </div>
                </div>
              );
            })}

            {fallbackChain.length === 0 ? (
              <div className="mt-2 rounded-lg border border-border/50 bg-secondary/10 p-2.5">
                <p className="text-center text-[10px] text-muted-foreground">No fallback is configured. The runtime will fail hard if the primary endpoint is unavailable.</p>
              </div>
            ) : (
              <div className="mt-2">
                <div className="flex justify-center py-1">
                  <ChevronRight className="h-3 w-3 rotate-90 text-muted-foreground" />
                </div>
                <div className="rounded-lg border border-border/50 bg-secondary/10 p-2.5 text-center">
                  <p className="text-[10px] text-muted-foreground">End of chain — fail hard if all fallback steps are exhausted.</p>
                </div>
              </div>
            )}
          </div>
        </GlassCard>

        <GlassCard>
          <div className="mb-3 flex items-center gap-2">
            <Layers className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Experimental / Informational Signals</h3>
            <Badge variant="outline" className="border-border/60 text-[9px] text-muted-foreground">
              Rebaixado
            </Badge>
          </div>
          <p className="mb-3 text-[10px] text-muted-foreground">
            These signals remain visible for demo and future evolution, but they are no longer promoted as primary controls in the main runtime path.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            <DiagnosticItem
              label="Grounding Strictness"
              value={profile.retrieval.groundingStrictness}
              description="Currently kept as an informational signal while grounding behavior is still largely shaped by the broader execution flow."
            />
            <DiagnosticItem
              label="Table Extraction Mode"
              value={profile.docProcessing.tableExtractionMode}
              description="Visible for future document pipeline evolution, but not treated as a first-class runtime knob today."
            />
            <DiagnosticItem
              label="Streaming"
              value={profile.generation.streaming ? 'Enabled' : 'Disabled'}
              description="Kept for explainability, but not emphasized as a primary runtime control on this screen."
            />
            <DiagnosticItem
              label="Structured Output"
              value={profile.generation.structuredOutput ? 'Enabled' : 'Disabled'}
              description="Useful for demo narratives, but not yet presented as a core end-to-end runtime control here."
            />
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}
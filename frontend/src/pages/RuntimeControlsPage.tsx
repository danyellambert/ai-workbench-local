import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  Cpu,
  FileText,
  Layers,
  Search,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
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
  formatRuntimeUpdatedAt,
  getRuntimeConnection,
} from '@/lib/runtime-controls-ui';
import type { RuntimeProfile } from '@/types/settings';

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
  const embeddingModelOptions = ((profile && data?.options.embeddingModelsByConnection[profile.embeddingConnectionId]) || []).filter(Boolean);


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
      const nextModel = modelOptions.includes(current.primaryModel) ? current.primaryModel : (modelOptions[0] || '');
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
      const nextModel = modelOptions.includes(current.embeddingModel)
        ? current.embeddingModel
        : (modelOptions[0] || current.embeddingModel || '');
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
          description="Active execution configuration for the current system profile — generation, retrieval, and document processing."
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
          description="Active execution configuration for the current system profile — generation, retrieval, and document processing."
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
      <div data-tour="runtime-controls-header">
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
      </div>

      <div className="space-y-6">
        {isError && (
          <GlassCard>
            <div className="flex items-center gap-2 text-xs text-glow-warning">
              <AlertTriangle className="h-4 w-4" />
              {error instanceof Error ? error.message : 'Runtime Controls loaded with backend caveats.'}
            </div>
          </GlassCard>
        )}

        <GlassCard data-tour="runtime-controls-summary">
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
            {(primaryConnection?.lastErrorMessage || embeddingConnection?.lastErrorMessage) ? (
              <div className="mb-4 rounded-lg border border-glow-warning/30 bg-glow-warning/10 px-3 py-2 text-[10px] text-glow-warning">
                <p className="font-medium text-foreground">Connection diagnostics</p>
                {primaryConnection?.lastErrorMessage ? (
                  <p className="mt-1">Generation connection: {primaryConnection.lastErrorMessage}</p>
                ) : null}
                {embeddingConnection?.lastErrorMessage ? (
                  <p className="mt-1">Embedding connection: {embeddingConnection.lastErrorMessage}</p>
                ) : null}
              </div>
            ) : null}
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

        <GlassCard data-tour="runtime-controls-generation">
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

        <GlassCard data-tour="runtime-controls-retrieval">
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
              {embeddingModelOptions.length > 0 ? (
                <Select value={profile.embeddingModel} onValueChange={(value) => updateProfile((current) => ({ ...current, embeddingModel: value }))}>
                  <SelectTrigger className="h-9 bg-secondary/30 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {embeddingModelOptions.map((model) => (
                      <SelectItem key={model} value={model}>{model}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div className="space-y-2">
                  <Input
                    value={profile.embeddingModel}
                    onChange={(event) => updateProfile((current) => ({ ...current, embeddingModel: event.target.value }))}
                    placeholder="Type the embedding model id manually"
                    className="h-9 bg-secondary/30 text-xs"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    No embedding models were discovered for this connection. Type the model id manually or configure the provider catalog/env so the backend can surface it here.
                  </p>
                </div>
              )}
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

        <GlassCard data-tour="runtime-controls-doc-processing">
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
            <ToggleRow label="OCR Recovery" description="Use OCR when extraction confidence drops below the configured threshold." checked={profile.docProcessing.ocrFailoverEnabled} onCheckedChange={(checked) => updateProfile((current) => ({ ...current, docProcessing: { ...current.docProcessing, ocrFailoverEnabled: checked } }))} />
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}
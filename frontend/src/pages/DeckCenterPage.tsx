import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Clock,
  Download,
  Eye,
  ExternalLink,
  FileOutput,
  FileText,
  FolderOpen,
  Layers,
  Loader2,
  Search,
  Sparkles,
} from 'lucide-react';

import { PageHeader, StatusPill, GlassCard, MetricCard } from '@/components/shared/ui-components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { formatUserDateTime, parseUserDateMs } from '@/lib/user-time';
import {
  buildProductArtifactUrl,
  getProductArtifactEntry,
  getProductArtifacts,
  type ProductArtifactAssetLink,
  type ProductArtifactEntry,
} from '@/lib/product-api';

const STATUS_OPTIONS = ['all', 'ready', 'warning', 'error', 'pending'] as const;
const DEFAULT_PAGE_SIZE = 24;

function formatDateTime(value?: string | number | null): string {
  return formatUserDateTime(value);
}

function safeNumber(value?: number | null, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function formatArtifactFocus(artifact: ProductArtifactEntry): string {
  const parts = [artifact.workflow_label, artifact.export_kind || artifact.type]
    .map((value) => String(value || '').trim())
    .filter(Boolean);
  return parts.join(' · ');
}

function openArtifactPath(path?: string | null): void {
  if (!path) return;
  window.open(buildProductArtifactUrl(path), '_blank', 'noopener,noreferrer');
}

function ArtifactAssetButton({ asset }: { asset: ProductArtifactAssetLink }) {
  return (
    <Button
      variant="outline"
      size="sm"
      className="h-8 text-[10px] border-border/50"
      disabled={!asset.available || !asset.path}
      onClick={() => openArtifactPath(asset.path)}
    >
      {asset.label}
      <ExternalLink className="ml-1 h-3 w-3" />
    </Button>
  );
}

function sortArtifacts(artifacts: ProductArtifactEntry[]): ProductArtifactEntry[] {
  return [...artifacts].sort((left, right) => {
    const leftTime = parseUserDateMs(left.created_at) ?? 0;
    const rightTime = parseUserDateMs(right.created_at) ?? 0;
    if (leftTime !== rightTime) return rightTime - leftTime;
    return (right.title || right.name).localeCompare(left.title || left.name);
  });
}

export default function DeckCenterPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_OPTIONS)[number]>('ready');
  const [selectedArtifactId, setSelectedArtifactId] = useState('');
  const [visibleCount, setVisibleCount] = useState(DEFAULT_PAGE_SIZE);

  const artifactsQuery = useQuery({
    queryKey: ['product-artifacts'],
    queryFn: getProductArtifacts,
    refetchOnWindowFocus: false,
  });

  const artifacts = artifactsQuery.data?.artifacts ?? [];
  const rankedArtifacts = useMemo(() => sortArtifacts(artifacts), [artifacts]);
  const workflowOptions = useMemo(
    () => ['all', ...Array.from(new Set(rankedArtifacts.map((artifact) => artifact.workflow_label).filter(Boolean)))],
    [rankedArtifacts],
  );
  const [workflowFilter, setWorkflowFilter] = useState('all');

  const filteredArtifacts = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return rankedArtifacts.filter((artifact) => {
      const matchesSearch =
        !needle ||
        `${artifact.name} ${artifact.title || ''} ${artifact.workflow_label} ${artifact.export_kind || ''} ${artifact.type} deck deck-center presentation executive artifact`
          .toLowerCase()
          .includes(needle);
      const matchesStatus = statusFilter === 'all' || artifact.status === statusFilter;
      const matchesWorkflow = workflowFilter === 'all' || artifact.workflow_label === workflowFilter;
      return matchesSearch && matchesStatus && matchesWorkflow;
    });
  }, [rankedArtifacts, search, statusFilter, workflowFilter]);

  const visibleArtifacts = useMemo(() => filteredArtifacts.slice(0, visibleCount), [filteredArtifacts, visibleCount]);
  const hiddenArtifactCount = Math.max(filteredArtifacts.length - visibleArtifacts.length, 0);
  const incompleteHiddenCount = useMemo(
    () => artifacts.filter((artifact) => artifact.status !== 'ready').length,
    [artifacts],
  );

  useEffect(() => {
    setVisibleCount(DEFAULT_PAGE_SIZE);
  }, [search, statusFilter, workflowFilter]);

  useEffect(() => {
    if (!visibleArtifacts.length) {
      setSelectedArtifactId('');
      return;
    }
    if (!selectedArtifactId || !visibleArtifacts.some((artifact) => artifact.id === selectedArtifactId)) {
      setSelectedArtifactId(visibleArtifacts[0].id);
    }
  }, [visibleArtifacts, selectedArtifactId]);

  const selectedArtifact = visibleArtifacts.find((artifact) => artifact.id === selectedArtifactId) ?? visibleArtifacts[0] ?? null;

  const artifactDetailQuery = useQuery({
    queryKey: ['product-artifact-entry', selectedArtifact?.id],
    queryFn: () => getProductArtifactEntry(selectedArtifact?.id || ''),
    enabled: Boolean(selectedArtifact?.id),
    refetchOnWindowFocus: false,
  });

  const detailArtifact = artifactDetailQuery.data?.artifact ?? selectedArtifact;
  const detail = artifactDetailQuery.data?.detail;
  const availableAssets = detail?.assets?.length ? detail.assets : detailArtifact?.available_assets ?? [];
  const primaryActions = [
    detailArtifact?.local_pptx_path ? { label: 'Presentation deck', path: detailArtifact.local_pptx_path } : null,
    detailArtifact?.local_review_path ? { label: 'Review report', path: detailArtifact.local_review_path } : null,
    detailArtifact?.local_payload_path ? { label: 'Source payload', path: detailArtifact.local_payload_path } : null,
    detailArtifact?.local_contract_path ? { label: 'Contract JSON', path: detailArtifact.local_contract_path } : null,
  ].filter(Boolean) as Array<{ label: string; path: string }>;

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="deck-center-header">
        <PageHeader title="Deck Center" description="Executive artifact catalog backed by the real export registry, persisted metadata, review sidecars and downloadable assets.">
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs" onClick={() => window.location.assign('/app/run')}>
            <Sparkles className="mr-2 h-3.5 w-3.5" /> Open Run Surface
          </Button>
        </PageHeader>
      </div>

      {(artifactsQuery.isError || artifactDetailQuery.isError) && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="h-4 w-4" />
            The artifact registry is live, but one or more detail sidecars could not be loaded. Ready decks and downloadable assets remain available.
          </div>
        </GlassCard>
      )}

      <div className="grid gap-3 md:grid-cols-4 mb-6" data-tour="deck-center-metrics">
        <MetricCard label="Artifacts" value={artifactsQuery.data?.summary.total_artifacts ?? artifacts.length} icon={FileOutput} delay={0.05} />
        <MetricCard label="Ready" value={artifactsQuery.data?.summary.completed_artifacts ?? artifacts.filter((artifact) => artifact.status === 'ready').length} icon={CheckCircle2} glowColor="success" delay={0.08} />
        <MetricCard label="Needs review" value={artifacts.filter((artifact) => artifact.status === 'warning').length} icon={AlertTriangle} glowColor="warning" delay={0.11} />
        <MetricCard label="Preview assets" value={artifacts.reduce((accumulator, artifact) => accumulator + safeNumber(artifact.preview_count), 0)} icon={Layers} glowColor="accent" delay={0.14} />
      </div>

      <GlassCard className="mb-4" data-tour="deck-center-filters">
        <div className="grid gap-3 md:grid-cols-[minmax(0,1.5fr)_180px_220px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search decks, export kinds, workflows or titles..." className="h-9 pl-9 text-xs" />
          </div>
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as (typeof STATUS_OPTIONS)[number])}>
            <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((status) => (
                <SelectItem key={status} value={status} className="text-xs capitalize">{status}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={workflowFilter} onValueChange={setWorkflowFilter}>
            <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue placeholder="Workflow" /></SelectTrigger>
            <SelectContent>
              {workflowOptions.map((workflow) => (
                <SelectItem key={workflow} value={workflow} className="text-xs">{workflow === 'all' ? 'All workflows' : workflow}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </GlassCard>

      <div className="mb-6 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <Badge variant="outline" className="border-border/60 text-[10px] text-muted-foreground">
          Showing {visibleArtifacts.length} of {filteredArtifacts.length}
        </Badge>
        {statusFilter === 'ready' && incompleteHiddenCount > 0 ? (
          <span>Non-ready exports stay out of the default view so the catalog reads as a deck center, not a raw artifact dump.</span>
        ) : null}
      </div>



      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(420px,0.9fr)]">
        <div className="space-y-3" data-tour="deck-center-list">
          {!visibleArtifacts.length && (
            <GlassCard>
              <div data-testid="deck-center-detail-empty" className="text-xs text-muted-foreground">
                {artifactsQuery.isLoading
                  ? 'Loading persisted deck artifacts...'
                  : 'No artifacts matched the current filters. Clear the search or switch the status filter to inspect incomplete exports.'}
              </div>
            </GlassCard>
          )}
          {visibleArtifacts.map((artifact, index) => {
            const isSelected = artifact.id === selectedArtifact?.id;
            const qualityLabel = typeof artifact.average_score === 'number' ? `${artifact.average_score.toFixed(1)}/10` : 'not scored yet';
            return (
              <motion.div
                key={artifact.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08 + index * 0.03 }}
                role="button"
                data-testid="deck-center-artifact-card"
                tabIndex={0}
                onClick={() => setSelectedArtifactId(artifact.id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    setSelectedArtifactId(artifact.id);
                  }
                }}
                className={`glass rounded-xl p-5 text-left transition-all duration-200 ${isSelected ? 'border-primary/40 bg-primary/5' : 'hover:border-primary/20'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <h3 className="text-sm font-medium text-foreground truncate">{artifact.title || artifact.name}</h3>
                      <StatusPill status={artifact.status} />
                    </div>
                    <p className="text-[11px] text-muted-foreground mb-2">{formatArtifactFocus(artifact)}</p>
                    <div className="grid gap-2 sm:grid-cols-2 text-[11px] text-muted-foreground">
                      <div className="flex items-center gap-2"><Clock className="h-3.5 w-3.5" /> {formatDateTime(artifact.created_at)}</div>
                      <div className="flex items-center gap-2"><Layers className="h-3.5 w-3.5" /> {artifact.slide_count ?? 0} slide(s) · {artifact.preview_count ?? 0} preview(s)</div>
                      <div className="flex items-center gap-2"><FileText className="h-3.5 w-3.5" /> {qualityLabel}</div>
                      <div className="flex items-center gap-2"><FolderOpen className="h-3.5 w-3.5" /> {artifact.asset_count ?? 0} file(s)</div>
                    </div>
                    {(artifact.status_reason || artifact.error_message || artifact.warnings?.length) && (
                      <p className="mt-2 text-[11px] text-glow-warning">
                        {artifact.status_reason || artifact.error_message || artifact.warnings?.[0]}
                      </p>
                    )}
                  </div>
                  {artifact.local_pptx_path ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-[10px] border-border/50"
                      onClick={(event) => {
                        event.stopPropagation();
                        openArtifactPath(artifact.local_pptx_path);
                      }}
                    >
                      Open <Eye className="ml-1 h-3 w-3" />
                    </Button>
                  ) : null}
                </div>
              </motion.div>
            );
          })}
          {hiddenArtifactCount > 0 ? (
            <Button variant="outline" className="w-full h-9 text-xs border-border/50" onClick={() => setVisibleCount((current) => current + DEFAULT_PAGE_SIZE)}>
              Show {Math.min(DEFAULT_PAGE_SIZE, hiddenArtifactCount)} more deck entries <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          ) : null}
        </div>

        <GlassCard className="min-h-[540px]" data-testid="deck-center-detail-panel" data-tour="deck-center-detail">
          {!detailArtifact ? (
            <div className="text-xs text-muted-foreground">Select an artifact to inspect its readiness, review snapshot, preview assets and export files.</div>
          ) : (
            <div className="space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="text-lg font-semibold text-foreground truncate">{detailArtifact.title || detailArtifact.name}</h3>
                    <StatusPill status={detailArtifact.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">{detailArtifact.workflow_label} · {detailArtifact.export_kind || detailArtifact.type}</p>
                  <p className="text-[11px] text-muted-foreground mt-1">Created {formatDateTime(detailArtifact.created_at)}</p>
                </div>
                {artifactDetailQuery.isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Slides</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{detailArtifact.slide_count ?? 0}</p>
                </div>
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Average review score</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{typeof detailArtifact.average_score === 'number' ? `${detailArtifact.average_score.toFixed(1)}/10` : 'Not reviewed yet'}</p>
                </div>
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Issues</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{safeNumber(detailArtifact.issue_count)} issue(s) · {safeNumber(detailArtifact.warning_count)} warning(s)</p>
                </div>
              </div>

              {primaryActions.length ? (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">Primary files</h4>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {primaryActions.map((action) => (
                      <Button key={action.label} variant="outline" className="justify-between" onClick={() => openArtifactPath(action.path)}>
                        {action.label} <ExternalLink className="h-4 w-4" />
                      </Button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-glow-warning/20 bg-glow-warning/5 p-3 text-xs text-glow-warning">
                  This export has metadata, but it does not yet look like a ready-to-review deck package. Switch the status filter to inspect incomplete or failed exports.
                </div>
              )}

              {detail?.preview_slides?.length ? (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">Preview slides</h4>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {detail.preview_slides.map((slide, index) => (
                      <button
                        type="button"
                        key={`${slide.path || slide.filename || index}`}
                        className="flex items-center justify-between rounded-lg border border-border/40 bg-secondary/10 px-3 py-2 text-left text-xs hover:border-primary/20"
                        disabled={!slide.available || !slide.path}
                        onClick={() => openArtifactPath(slide.path)}
                      >
                        <span className="truncate">Slide {slide.slide_number ?? index + 1} · {slide.filename || 'preview'}</span>
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground">Readiness snapshot</h4>
                  <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                    <div>Status: {detailArtifact.review_status || detailArtifact.status}</div>
                    <div>Has preview: {detailArtifact.has_preview ? 'yes' : 'no'}</div>
                    <div>Has review: {detailArtifact.has_review ? 'yes' : 'no'}</div>
                    <div>Size: {detailArtifact.size || 'n/a'}</div>
                  </div>
                </div>
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground">Registry notes</h4>
                  <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                    {(detail?.notes?.length ? detail.notes : [detailArtifact.status_reason || detailArtifact.error_message || 'No additional notes for this export.']).map((note) => (
                      <p key={note}>{note}</p>
                    ))}
                  </div>
                </div>
              </div>

              {availableAssets.length ? (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">All registry assets</h4>
                  <div className="flex flex-wrap gap-2">
                    {availableAssets.map((asset) => <ArtifactAssetButton key={`${asset.artifact_type}:${asset.path || asset.label}`} asset={asset} />)}
                  </div>
                </div>
              ) : null}

              <details className="rounded-lg border border-border/40 bg-secondary/10 p-0">
                <summary className="cursor-pointer list-none px-3 py-2 text-xs font-medium text-foreground">Technical registry details</summary>
                <div className="border-t border-border/40 px-3 py-3 text-xs text-muted-foreground space-y-1">
                  <div>Metadata path: {detailArtifact.metadata_path || 'n/a'}</div>
                  <div>Artifact dir: {detailArtifact.local_artifact_dir || 'n/a'}</div>
                  <div>Preview manifest: {detailArtifact.local_preview_manifest_path || 'n/a'}</div>
                  <div>Render request: {detailArtifact.local_render_request_path || 'n/a'}</div>
                  <div>Render response: {detailArtifact.local_render_response_path || 'n/a'}</div>
                </div>
              </details>
            </div>
          )}
        </GlassCard>
      </div>
    </motion.div>
  );
}

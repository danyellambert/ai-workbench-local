import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, ExternalLink, FolderTree, KanbanSquare, Loader2, RefreshCw, ScrollText } from 'lucide-react';

import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { Button } from '@/components/ui/button';
import {
  getProductIntegrationHub,
  getProductNextcloudDocuments,
  getProductNotionEntries,
  publishProductWorkflowToNotion,
  publishProductWorkflowToTrello,
  syncProductEvidenceToNextcloud,
  type ProductNextcloudDocument,
  type ProductNextcloudSyncResponse,
  type ProductPublishNotionResponse,
  type ProductPublishTrelloResponse,
} from '@/lib/product-api';
import { toast } from '@/components/ui/sonner';

import { formatUserDateTime } from '@/lib/user-time';
type DeliveryLoopPanelProps = {
  title?: string;
  description?: string;
  workflowId?: string | null;
  result?: Record<string, unknown> | null;
  runId?: string | null;
  showActions?: boolean;
  compact?: boolean;
  className?: string;
  onTrelloPublished?: (payload: ProductPublishTrelloResponse) => void;
  onNotionPublished?: (payload: ProductPublishNotionResponse) => void;
  onNextcloudSynced?: (payload: ProductNextcloudSyncResponse) => void;
};

function formatDateTime(value?: string | number | null): string {
  return formatUserDateTime(value);
}

function formatDocumentTimestamp(value?: string | number | null): string {
  return formatUserDateTime(value);
}

function looksOpaque(value?: string | null): boolean {
  const normalized = String(value || '').replace(/[^a-zA-Z0-9]/g, '');
  if (normalized.length < 24) return false;
  if (/^[0-9a-f]+$/i.test(normalized)) return true;
  const digits = (normalized.match(/[0-9]/g) || []).length;
  const letters = (normalized.match(/[a-z]/gi) || []).length;
  return digits >= 8 && letters >= 8;
}

function sanitizeTitle(value?: string | null, fallback = 'Executive handoff'): string {
  const normalized = String(value || '').trim();
  if (!normalized || looksOpaque(normalized) || /^untitled\b/i.test(normalized)) return fallback;
  return normalized.length > 72 ? `${normalized.slice(0, 71).trimEnd()}…` : normalized;
}

function sanitizeMetricValue(value: string | number): string | number {
  if (typeof value !== 'string') return value;
  return looksOpaque(value) ? 'Configured' : value;
}

function summarizeTarget(key: string, configured: boolean, lastSummary?: string | null): string {
  if (lastSummary && lastSummary.trim()) return lastSummary;
  if (!configured) return `${key === 'nextcloud' ? 'Corpus import/export' : key === 'trello' ? 'Operational publishing' : 'Executive handoff'} is not configured.`;
  if (key === 'nextcloud') return 'Remote corpus available for import and export.';
  if (key === 'trello') return 'Operational workspace ready for task publishing.';
  return 'Executive workspace ready for summary publishing.';
}

function normalizeDocuments(documents: ProductNextcloudDocument[]) {
  return documents.map((document) => ({
    ...document,
    title: sanitizeTitle(document.title, 'Untitled document'),
  }));
}

export function DeliveryLoopPanel({
  title = 'Connected delivery targets',
  description = 'Review where evidence comes from, where execution lands and where executive handoffs publish.',
  workflowId,
  result,
  runId,
  showActions = false,
  compact = false,
  className,
  onTrelloPublished,
  onNotionPublished,
  onNextcloudSynced,
}: DeliveryLoopPanelProps) {
  const queryClient = useQueryClient();

  const hubQuery = useQuery({
    queryKey: ['product-integrations'],
    queryFn: getProductIntegrationHub,
    refetchOnWindowFocus: false,
  });

  const notionQuery = useQuery({
    queryKey: ['product-integrations', 'notion-entries'],
    queryFn: () => getProductNotionEntries(compact ? 4 : 6),
    refetchOnWindowFocus: false,
  });

  const nextcloudQuery = useQuery({
    queryKey: ['product-integrations', 'nextcloud-documents'],
    queryFn: () => getProductNextcloudDocuments(compact ? 6 : 10),
    refetchOnWindowFocus: false,
  });

  const refreshIntegrationQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['product-integrations'] }),
      queryClient.invalidateQueries({ queryKey: ['product-integrations', 'notion-entries'] }),
      queryClient.invalidateQueries({ queryKey: ['product-integrations', 'nextcloud-documents'] }),
      queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
      queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
    ]);
  };

  const publishTrelloMutation = useMutation({
    mutationFn: async () => {
      if (!result) throw new Error('Run the workflow before publishing to Trello.');
      return publishProductWorkflowToTrello(result, { runId });
    },
    onSuccess: async (payload) => {
      await refreshIntegrationQueries();
      const count = Number(payload.created_card_count || payload.planned_card_count || 0);
      toast.success(payload.message || (count > 0 ? `Published ${count} Trello card(s).` : 'Published the run to Trello.'));
      onTrelloPublished?.(payload);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Trello publish failed.'),
  });

  const publishNotionMutation = useMutation({
    mutationFn: async () => {
      if (!result) throw new Error('Run the workflow before publishing to Notion.');
      return publishProductWorkflowToNotion(result, { runId });
    },
    onSuccess: async (payload) => {
      await refreshIntegrationQueries();
      toast.success(payload.message || 'Published the current run to Notion.');
      onNotionPublished?.(payload);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Notion publish failed.'),
  });

  const syncNextcloudMutation = useMutation({
    mutationFn: () => syncProductEvidenceToNextcloud(),
    onSuccess: async (payload) => {
      await refreshIntegrationQueries();
      const count = Number(payload.upload_count || payload.uploaded_file_count || 0);
      toast.success(payload.message || (count > 0 ? `Synced ${count} file(s) to Nextcloud.` : 'Nextcloud sync completed.'));
      onNextcloudSynced?.(payload);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Nextcloud sync failed.'),
  });

  const hubData = hubQuery.data;
  const workflowTarget = useMemo(
    () => hubData?.workflow_targets?.find((item) => item.workflow_id === workflowId) ?? null,
    [hubData?.workflow_targets, workflowId],
  );
  const recentDeliveries = useMemo(
    () => (workflowId ? (hubData?.recent_deliveries ?? []).filter((item) => item.workflow_id === workflowId).slice(0, compact ? 3 : 4) : (hubData?.recent_deliveries ?? []).slice(0, compact ? 3 : 4)),
    [compact, hubData?.recent_deliveries, workflowId],
  );

  const normalizedNotionEntries = useMemo(
    () => (notionQuery.data?.entries ?? []).map((entry) => ({ ...entry, title: sanitizeTitle(entry.title) })),
    [notionQuery.data?.entries],
  );
  const normalizedNextcloudDocuments = useMemo(
    () => normalizeDocuments(nextcloudQuery.data?.documents ?? []),
    [nextcloudQuery.data?.documents],
  );

  const targetIcons = {
    nextcloud: FolderTree,
    trello: KanbanSquare,
    notion: ScrollText,
  } as const;

  return (
    <GlassCard className={className} data-testid="delivery-loop-panel">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-medium text-foreground">{title}</h3>
              <StatusPill status={hubData?.status || 'pending'} />
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
            {workflowTarget ? <p className="mt-2 text-[11px] text-muted-foreground">{workflowTarget.narrative}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" className="h-8 border-border/50 text-[10px]" onClick={() => { void hubQuery.refetch(); void notionQuery.refetch(); void nextcloudQuery.refetch(); }}>
              <RefreshCw className="mr-1 h-3.5 w-3.5" /> Refresh
            </Button>
            {showActions ? (
              <>
                <Button variant="outline" size="sm" className="h-8 border-border/50 text-[10px]" disabled={!result || publishTrelloMutation.isPending} onClick={() => publishTrelloMutation.mutate()}>
                  {publishTrelloMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <KanbanSquare className="mr-1 h-3.5 w-3.5" />} Publish Trello
                </Button>
                <Button variant="outline" size="sm" className="h-8 border-border/50 text-[10px]" disabled={!result || publishNotionMutation.isPending} onClick={() => publishNotionMutation.mutate()}>
                  {publishNotionMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <ScrollText className="mr-1 h-3.5 w-3.5" />} Publish Notion
                </Button>
                <Button variant="outline" size="sm" className="h-8 border-border/50 text-[10px]" disabled={syncNextcloudMutation.isPending} onClick={() => syncNextcloudMutation.mutate()}>
                  {syncNextcloudMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <FolderTree className="mr-1 h-3.5 w-3.5" />} Sync Nextcloud
                </Button>
              </>
            ) : null}
          </div>
        </div>

        {!!hubData?.cycle?.length && !compact ? (
          <div className="grid gap-2 md:grid-cols-4">
            {hubData.cycle.map((step, index) => (
              <div key={`${step.step}-${step.target}`} className="rounded-lg border border-border/40 bg-secondary/10 px-3 py-2">
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                  <span>{index + 1}</span>
                  <ArrowRight className="h-3 w-3" />
                  <span>{step.step}</span>
                </div>
                <p className="mt-1 text-xs font-medium capitalize text-foreground">{step.target}</p>
                <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">{step.description}</p>
              </div>
            ))}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-3">
          {(hubData?.targets ?? []).map((target) => {
            const Icon = targetIcons[target.key as keyof typeof targetIcons] ?? FolderTree;
            return (
              <div key={target.key} className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background/80">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-foreground">{target.label}</p>
                      <p className="text-[10px] text-muted-foreground">{target.role}</p>
                    </div>
                  </div>
                  <StatusPill status={target.status || (target.configured ? 'ready' : 'degraded')} />
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">{summarizeTarget(target.key, target.configured, target.last_delivery_summary)}</p>
                {!!target.metrics?.length && (
                  <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
                    {target.metrics.slice(0, compact ? 1 : 4).map((metric) => (
                      <div key={`${target.key}-${metric.label}`} className="rounded-md bg-background/70 px-2 py-2">
                        <div className="uppercase tracking-wide text-muted-foreground">{metric.label}</div>
                        <div className="mt-1 text-sm font-medium text-foreground">{sanitizeMetricValue(metric.value)}</div>
                      </div>
                    ))}
                  </div>
                )}
                {target.last_delivery_at ? (
                  <p className="mt-3 text-[10px] text-muted-foreground">Last delivery · {formatDateTime(target.last_delivery_at)}</p>
                ) : null}
              </div>
            );
          })}
        </div>

        <div className={`grid gap-3 ${compact ? 'lg:grid-cols-[1.2fr_0.8fr]' : 'xl:grid-cols-[1.05fr_0.95fr_1fr]'}`}>
          <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h4 className="text-xs font-medium text-foreground">Recent deliveries</h4>
              <span className="text-[10px] text-muted-foreground">{hubData?.summary.recent_deliveries ?? 0} tracked</span>
            </div>
            <div className="space-y-2">
              {(compact ? recentDeliveries.slice(0, 2) : recentDeliveries).length ? (compact ? recentDeliveries.slice(0, 2) : recentDeliveries).map((delivery) => (
                <div key={`${delivery.run_id || 'global'}-${delivery.target}-${delivery.timestamp || delivery.summary || 'recent'}`} className="rounded-md bg-background/70 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-medium text-foreground">{delivery.target_label}</p>
                    <StatusPill status={delivery.status || 'pending'} />
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground">{delivery.workflow_label || 'Cross-workflow delivery'} · {formatDateTime(delivery.timestamp)}</p>
                  {delivery.summary ? <p className="mt-1 text-[11px] text-muted-foreground">{sanitizeTitle(delivery.summary, 'Recent delivery')}</p> : null}
                  {delivery.url ? (
                    <button type="button" className="mt-2 inline-flex items-center gap-1 text-[10px] text-primary hover:underline" onClick={() => window.open(delivery.url || '', '_blank', 'noopener,noreferrer')}>
                      Open remote target <ExternalLink className="h-3 w-3" />
                    </button>
                  ) : null}
                </div>
              )) : <p className="text-xs text-muted-foreground">No external delivery has been recorded yet for this view.</p>}
            </div>
          </div>

          {compact ? (
            <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-3">
                <h4 className="text-xs font-medium text-foreground">Live surfaces</h4>
                <span className="text-[10px] text-muted-foreground">clean summary</span>
              </div>
              <div className="space-y-2">
                {normalizedNotionEntries.slice(0, 1).map((entry) => (
                  <div key={entry.id} className="rounded-md bg-background/70 px-3 py-2">
                    <p className="text-xs font-medium text-foreground">{sanitizeTitle(entry.title)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">Notion handoff · {formatDateTime(entry.last_edited_time || entry.created_time)}</p>
                  </div>
                ))}
                {normalizedNextcloudDocuments.slice(0, 1).map((document) => (
                  <div key={`${document.relative_path || document.title}-${document.modified_at || 'doc'}`} className="rounded-md bg-background/70 px-3 py-2">
                    <p className="text-xs font-medium text-foreground">{sanitizeTitle(document.title, 'Corpus file')}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">Nextcloud corpus · {document.relative_path || document.category || 'remote file'}</p>
                  </div>
                ))}
                {!normalizedNotionEntries.length && !normalizedNextcloudDocuments.length ? <p className="text-xs text-muted-foreground">Waiting for live Nextcloud and Notion surface data.</p> : null}
              </div>
            </div>
          ) : (
            <>
              <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <h4 className="text-xs font-medium text-foreground">Notion handoffs</h4>
                  <span className="text-[10px] text-muted-foreground">{notionQuery.data?.entry_count ?? 0} entries</span>
                </div>
                <div className="space-y-2">
                  {normalizedNotionEntries.length ? normalizedNotionEntries.map((entry) => (
                    <div key={entry.id} className="rounded-md bg-background/70 px-3 py-2">
                      <p className="text-xs font-medium text-foreground">{sanitizeTitle(entry.title)}</p>
                      <p className="mt-1 text-[10px] text-muted-foreground">Edited {formatDateTime(entry.last_edited_time || entry.created_time)}</p>
                      {entry.page_url ? (
                        <button type="button" className="mt-2 inline-flex items-center gap-1 text-[10px] text-primary hover:underline" onClick={() => window.open(entry.page_url || '', '_blank', 'noopener,noreferrer')}>
                          Open page <ExternalLink className="h-3 w-3" />
                        </button>
                      ) : null}
                    </div>
                  )) : <p className="text-xs text-muted-foreground">No Notion pages were discovered from the configured workspace yet.</p>}
                </div>
              </div>

              <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <h4 className="text-xs font-medium text-foreground">Nextcloud evidence</h4>
                  <span className="text-[10px] text-muted-foreground">{nextcloudQuery.data?.entry_count ?? 0} docs</span>
                </div>
                <div className="space-y-2">
                  {normalizedNextcloudDocuments.length ? normalizedNextcloudDocuments.map((document) => (
                    <div key={`${document.relative_path || document.title}-${document.modified_at || 'doc'}`} className="rounded-md bg-background/70 px-3 py-2">
                      <p className="text-xs font-medium text-foreground">{sanitizeTitle(document.title, 'Corpus file')}</p>
                      <p className="mt-1 text-[10px] text-muted-foreground">{document.category || 'document'} · {document.relative_path || 'remote file'}</p>
                      <p className="mt-1 text-[10px] text-muted-foreground">Updated {formatDocumentTimestamp(document.modified_at)}</p>
                    </div>
                  )) : <p className="text-xs text-muted-foreground">Nextcloud corpus mapping is ready, but no remote documents were listed yet.</p>}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

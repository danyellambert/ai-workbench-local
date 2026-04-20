import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, KanbanSquare, Loader2, ScrollText } from 'lucide-react';

import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from '@/components/ui/sonner';
import { cn } from '@/lib/utils';
import {
  getProductIntegrationHub,
  publishProductWorkflowToNotion,
  publishProductWorkflowToTrello,
  type ProductPublishNotionResponse,
  type ProductPublishTrelloResponse,
} from '@/lib/product-api';

type WorkflowPublishActionsProps = {
  workflowId: string;
  result?: Record<string, unknown> | null;
  runId?: string | null;
  title?: string;
  description?: string;
  className?: string;
  notionPreviewPayload?: Record<string, unknown> | null;
  onTrelloPublished?: (payload: ProductPublishTrelloResponse) => void;
  onNotionPublished?: (payload: ProductPublishNotionResponse) => void;
};

type PreviewTarget = 'trello' | 'notion' | null;

type NotionTemplateOption = {
  id: string;
  label: string;
  description: string;
};

type TrelloPreviewCard = Record<string, unknown>;

type TrelloPreviewSection = {
  heading: string;
  items: string[];
};

const NOTION_TEMPLATE_OPTIONS: Record<string, NotionTemplateOption[]> = {
  action_plan_evidence_review: [
    { id: 'action_register', label: 'Action register', description: 'Owners, priorities and due dates.' },
    { id: 'executive_summary', label: 'Executive summary', description: 'Narrative handoff for stakeholders.' },
    { id: 'evidence_gaps', label: 'Evidence gaps', description: 'Missing evidence before execution.' },
  ],
  candidate_review: [
    { id: 'candidate_brief', label: 'Candidate brief', description: 'Hiring summary with strengths and risks.' },
    { id: 'interview_plan', label: 'Interview plan', description: 'Validation focus for interviewers.' },
  ],
  document_review: [
    { id: 'review_summary', label: 'Review summary', description: 'Decision summary and next steps.' },
    { id: 'findings_register', label: 'Findings register', description: 'Structured finding log and remediation.' },
  ],
  policy_contract_comparison: [
    { id: 'comparison_memo', label: 'Comparison memo', description: 'Executive delta summary.' },
    { id: 'remediation_register', label: 'Remediation register', description: 'Must-fix items and negotiation priorities.' },
  ],
};

function getWorkflowTemplateOptions(workflowId: string): NotionTemplateOption[] {
  return NOTION_TEMPLATE_OPTIONS[workflowId] ?? [{ id: 'executive_summary', label: 'Executive summary', description: 'Default workflow handoff.' }];
}

function isTargetReady(status?: string | null): boolean {
  const normalized = String(status || '').trim().toLowerCase();
  return normalized === 'ready' || normalized === 'live' || normalized === 'completed' || normalized === 'success';
}

function displayLabel(value: unknown, fallback: string): string {
  const normalized = String(value || '').trim();
  if (!normalized || /^untitled\b/i.test(normalized)) return fallback;
  return normalized.length > 88 ? `${normalized.slice(0, 87).trimEnd()}…` : normalized;
}

function compactText(value: unknown, fallback = '—', maxChars = 140): string {
  const normalized = String(value || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return fallback;
  return normalized.length > maxChars ? `${normalized.slice(0, maxChars - 1).trimEnd()}…` : normalized;
}

function normalizeExternalUrl(value: unknown): string | null {
  const raw = String(value || '').trim();
  if (!raw || raw.toLowerCase() === 'about:blank') return null;
  try {
    const parsed = new URL(raw);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.toString() : null;
  } catch {
    return null;
  }
}

function buildTrelloBoardFallbackUrl(boardId: unknown): string | null {
  const normalized = String(boardId || '').trim();
  if (!normalized) return null;
  return `https://trello.com/b/${encodeURIComponent(normalized)}`;
}

function splitPreviewItems(value: string, limit = 6): string[] {
  return value
    .split(/\n+|\s+[\u2022\-]\s+|\s+\*\*[^*]+\*\*:?\s*/g)
    .map((item) => item.replace(/^[-•]\s*/, '').trim())
    .filter(Boolean)
    .slice(0, limit);
}

function parseTrelloCard(card: TrelloPreviewCard | null): { title: string; listLabel: string; summary: string | null; sections: TrelloPreviewSection[] } {
  const title = displayLabel(card?.name || card?.title, 'Card');
  const listLabel = displayLabel(card?.list_label || card?.list_name, 'Mapped list');
  const description = String(card?.description || '').replace(/\r\n/g, '\n').trim();
  if (!description) {
    return { title, listLabel, summary: null, sections: [] };
  }

  const lines = description.split('\n').map((line) => line.trim()).filter(Boolean);
  const sections: TrelloPreviewSection[] = [];
  let currentHeading = 'Details';
  let currentItems: string[] = [];
  let summary: string | null = null;

  const flushSection = () => {
    const normalizedItems = currentItems.flatMap((item) => splitPreviewItems(item, 8)).filter(Boolean);
    if (normalizedItems.length) {
      sections.push({ heading: currentHeading, items: Array.from(new Set(normalizedItems)).slice(0, 8) });
    }
    currentItems = [];
  };

  for (const line of lines) {
    if (/^##\s+/.test(line)) {
      continue;
    }
    if (/^###\s+/.test(line)) {
      flushSection();
      currentHeading = line.replace(/^###\s+/, '').trim() || 'Details';
      continue;
    }
    if (!summary) {
      const candidate = compactText(line, '', 220);
      summary = candidate || null;
    }
    currentItems.push(line);
  }
  flushSection();

  if (!sections.length && description) {
    sections.push({ heading: 'Details', items: splitPreviewItems(description, 8) });
  }

  return { title, listLabel, summary, sections };
}

function openExternalUrl(url: string | null, fallbackMessage: string): void {
  if (!url) {
    toast.error(fallbackMessage);
    return;
  }
  const opened = window.open(url, '_blank');
  if (!opened) {
    toast.error('The browser blocked the preview tab. Allow pop-ups for this site and try again.');
  }
}

export function WorkflowPublishActions({
  workflowId,
  result,
  runId,
  title = 'Publish outputs',
  description = 'Review what will be published before sending it to Trello or Notion.',
  className,
  notionPreviewPayload,
  onTrelloPublished,
  onNotionPublished,
}: WorkflowPublishActionsProps) {
  const queryClient = useQueryClient();
  const [dialogTarget, setDialogTarget] = useState<PreviewTarget>(null);
  const templateOptions = useMemo(() => getWorkflowTemplateOptions(workflowId), [workflowId]);
  const [selectedTemplateId, setSelectedTemplateId] = useState(templateOptions[0]?.id ?? 'executive_summary');
  const [selectedTrelloCardIndex, setSelectedTrelloCardIndex] = useState(0);
  const [trelloPreview, setTrelloPreview] = useState<ProductPublishTrelloResponse | null>(null);
  const [notionPreview, setNotionPreview] = useState<ProductPublishNotionResponse | null>(null);

  const hubQuery = useQuery({
    queryKey: ['product-integrations'],
    queryFn: getProductIntegrationHub,
    refetchOnWindowFocus: false,
  });

  const refreshProductQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['product-integrations'] }),
      queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
      queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      queryClient.invalidateQueries({ queryKey: ['product-artifacts'] }),
    ]);
  };

  const trelloTarget = hubQuery.data?.targets?.find((target) => target.key === 'trello');
  const notionTarget = hubQuery.data?.targets?.find((target) => target.key === 'notion');

  const previewTrelloMutation = useMutation({
    mutationFn: async () => {
      if (!result) throw new Error('Run the workflow before previewing the Trello publish.');
      return publishProductWorkflowToTrello(result, { runId, dryRun: true, previewPayload: notionPreviewPayload ?? undefined });
    },
    onSuccess: (payload) => {
      setTrelloPreview(payload);
      setDialogTarget('trello');
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Trello preview failed.'),
  });

  const publishTrelloMutation = useMutation({
    mutationFn: async () => {
      if (!result) throw new Error('Run the workflow before publishing to Trello.');
      return publishProductWorkflowToTrello(result, { runId, dryRun: false, previewPayload: notionPreviewPayload ?? undefined });
    },
    onSuccess: async (payload) => {
      await refreshProductQueries();
      onTrelloPublished?.(payload);
      setDialogTarget(null);
      toast.success(payload.message || 'Published to Trello.');
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Trello publish failed.'),
  });

  const previewNotionMutation = useMutation({
    mutationFn: async (templateId: string) => {
      if (!result) throw new Error('Run the workflow before previewing the Notion publish.');
      return publishProductWorkflowToNotion(result, {
        runId,
        dryRun: true,
        templateId,
        previewPayload: notionPreviewPayload ?? undefined,
      });
    },
    onSuccess: (payload) => {
      setNotionPreview(payload);
      setDialogTarget('notion');
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Notion preview failed.'),
  });

  const publishNotionMutation = useMutation({
    mutationFn: async (templateId: string) => {
      if (!result) throw new Error('Run the workflow before publishing to Notion.');
      return publishProductWorkflowToNotion(result, {
        runId,
        dryRun: false,
        templateId,
        previewPayload: notionPreviewPayload ?? undefined,
      });
    },
    onSuccess: async (payload) => {
      await refreshProductQueries();
      onNotionPublished?.(payload);
      setDialogTarget(null);
      toast.success(payload.message || 'Published to Notion.');
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Notion publish failed.'),
  });

  const selectedTemplate = templateOptions.find((item) => item.id === selectedTemplateId) ?? templateOptions[0];
  const trelloCards = useMemo(() => (
    Array.isArray(trelloPreview?.planned_cards) ? (trelloPreview?.planned_cards as TrelloPreviewCard[]) : []
  ), [trelloPreview]);
  const activeTrelloCard = useMemo(() => {
    if (!trelloCards.length) return null;
    const safeIndex = Math.min(selectedTrelloCardIndex, trelloCards.length - 1);
    return trelloCards[safeIndex] ?? null;
  }, [selectedTrelloCardIndex, trelloCards]);
  const parsedActiveTrelloCard = useMemo(() => parseTrelloCard(activeTrelloCard), [activeTrelloCard]);
  const trelloOpenUrl = useMemo(() => normalizeExternalUrl(
    trelloPreview?.board_url
    || (Array.isArray(trelloPreview?.created_card_urls) ? trelloPreview?.created_card_urls?.[0] : null)
    || buildTrelloBoardFallbackUrl(trelloPreview?.target_board_id),
  ), [trelloPreview]);
  const notionOpenUrl = useMemo(() => normalizeExternalUrl(notionPreview?.page_url), [notionPreview]);

  useEffect(() => {
    if (dialogTarget === 'trello') {
      setSelectedTrelloCardIndex(0);
    }
  }, [dialogTarget, trelloPreview?.planned_card_count]);

  return (
    <>
      <GlassCard className={className} data-testid="workflow-publish-actions">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-medium text-foreground">{title}</h3>
              <StatusPill status={hubQuery.data?.status || 'pending'} />
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant="outline" className={cn('text-[10px]', isTargetReady(trelloTarget?.status) ? 'border-primary/30 text-primary' : 'border-border/60 text-muted-foreground')}>
                Trello {isTargetReady(trelloTarget?.status) ? 'connected' : 'degraded'}
              </Badge>
              <Badge variant="outline" className={cn('text-[10px]', isTargetReady(notionTarget?.status) ? 'border-primary/30 text-primary' : 'border-border/60 text-muted-foreground')}>
                Notion {isTargetReady(notionTarget?.status) ? 'connected' : 'degraded'}
              </Badge>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap lg:justify-end">
            <Button
              variant="outline"
              size="sm"
              className="h-8 border-border/50 text-[10px]"
              data-testid="workflow-preview-trello"
              disabled={!result || previewTrelloMutation.isPending || publishTrelloMutation.isPending}
              onClick={() => previewTrelloMutation.mutate()}
            >
              {previewTrelloMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <KanbanSquare className="mr-1 h-3.5 w-3.5" />}
              Preview Trello
            </Button>

            <div className="flex items-center gap-2">
              <Select value={selectedTemplateId} onValueChange={setSelectedTemplateId}>
                <SelectTrigger data-testid="workflow-template-select" className="h-8 min-w-[180px] border-border/50 bg-background/70 text-[10px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {templateOptions.map((option) => (
                    <SelectItem key={option.id} value={option.id} className="text-xs">
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                className="h-8 border-border/50 text-[10px]"
                data-testid="workflow-preview-notion"
                disabled={!result || previewNotionMutation.isPending || publishNotionMutation.isPending}
                onClick={() => previewNotionMutation.mutate(selectedTemplateId)}
              >
                {previewNotionMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <ScrollText className="mr-1 h-3.5 w-3.5" />}
                Preview Notion
              </Button>
            </div>
          </div>
        </div>
      </GlassCard>

      <Dialog open={dialogTarget !== null} onOpenChange={(open) => !open && setDialogTarget(null)}>
        <DialogContent className="max-h-[88vh] overflow-hidden border-border/60 bg-background/95 sm:max-w-5xl">
          {dialogTarget === 'trello' ? (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 text-base">
                  <KanbanSquare className="h-4 w-4 text-primary" /> Trello preview
                </DialogTitle>
                <DialogDescription>
                  Review the cards that will be created before publishing this workflow result.
                </DialogDescription>
              </DialogHeader>
              <div className="grid min-h-0 gap-4 py-2 md:grid-cols-[0.92fr_1.08fr]">
                <div className="flex min-h-0 flex-col gap-4">
                  <div className="rounded-lg border border-border/50 bg-secondary/10 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Planned cards</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{trelloPreview?.planned_card_count ?? 0}</p>
                    {trelloPreview?.message ? <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{trelloPreview.message}</p> : null}
                    {trelloPreview?.list_breakdown?.length ? (
                      <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
                        {trelloPreview.list_breakdown.map((entry) => (
                          <div key={`${entry.list_id || entry.list_label}`} className="rounded-md bg-background/80 px-2 py-2">
                            <div className="text-muted-foreground uppercase tracking-wide">{entry.list_label || entry.list_name || 'List'}</div>
                            <div className="mt-1 text-sm font-medium text-foreground">{entry.count ?? entry.planned_card_count ?? 0}</div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="min-h-0 rounded-lg border border-border/50 bg-secondary/10 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Card queue</p>
                    <ScrollArea className="mt-3 h-[360px] pr-3">
                      <div className="space-y-2">
                        {trelloCards.length ? trelloCards.map((card, index) => {
                          const parsed = parseTrelloCard(card);
                          const isActive = index === selectedTrelloCardIndex;
                          return (
                            <button
                              key={`${parsed.title}-${index}`}
                              type="button"
                              onClick={() => setSelectedTrelloCardIndex(index)}
                              className={cn(
                                'w-full rounded-md border px-3 py-3 text-left transition-colors',
                                isActive ? 'border-primary/40 bg-primary/10' : 'border-border/50 bg-background/80 hover:border-primary/20 hover:bg-background',
                              )}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <p className="text-xs font-medium text-foreground">{parsed.title}</p>
                                  <p className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">{parsed.listLabel}</p>
                                </div>
                                <Badge variant="outline" className="shrink-0 text-[9px]">#{index + 1}</Badge>
                              </div>
                              {parsed.summary ? <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{parsed.summary}</p> : null}
                            </button>
                          );
                        }) : <p className="text-xs text-muted-foreground">No Trello cards were planned yet.</p>}
                      </div>
                    </ScrollArea>
                  </div>
                </div>

                <div className="min-h-0 rounded-lg border border-border/50 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Card preview</p>
                  {activeTrelloCard ? (
                    <>
                      <div className="mt-3 rounded-md bg-background/80 px-3 py-3">
                        <p className="text-sm font-medium text-foreground">{parsedActiveTrelloCard.title}</p>
                        <p className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">{parsedActiveTrelloCard.listLabel}</p>
                        {parsedActiveTrelloCard.summary ? <p className="mt-3 text-[12px] leading-relaxed text-muted-foreground">{parsedActiveTrelloCard.summary}</p> : null}
                      </div>
                      <ScrollArea className="mt-3 h-[430px] pr-3">
                        <div className="space-y-3">
                          {parsedActiveTrelloCard.sections.map((section) => (
                            <div key={section.heading} className="rounded-md bg-background/80 px-3 py-2">
                              <p className="text-xs font-medium text-foreground">{section.heading}</p>
                              <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                                {section.items.map((item) => <li key={item} className="leading-relaxed">• {item}</li>)}
                              </ul>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </>
                  ) : <p className="mt-3 text-xs text-muted-foreground">Select a planned card to inspect the publish preview.</p>}
                </div>
              </div>
              <DialogFooter className="gap-2 sm:justify-between">
                <p className="text-[11px] text-muted-foreground">The publish action will create the cards shown in this preview.</p>
                <div className="flex items-center gap-2">
                  {trelloOpenUrl ? (
                    <Button variant="outline" onClick={() => openExternalUrl(trelloOpenUrl, 'This Trello preview does not expose a board URL yet.')}>
                      Open page <ExternalLink className="ml-2 h-4 w-4" />
                    </Button>
                  ) : null}
                  <Button disabled={publishTrelloMutation.isPending} onClick={() => publishTrelloMutation.mutate()}>
                    {publishTrelloMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KanbanSquare className="mr-2 h-4 w-4" />}
                    Publish to Trello
                  </Button>
                </div>
              </DialogFooter>
            </>
          ) : null}

          {dialogTarget === 'notion' ? (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 text-base">
                  <ScrollText className="h-4 w-4 text-primary" /> Notion preview
                </DialogTitle>
                <DialogDescription>
                  Review the template and sections that will be published to Notion.
                </DialogDescription>
              </DialogHeader>
              <div className="grid min-h-0 gap-4 py-2 md:grid-cols-[0.82fr_1.18fr]">
                <div className="min-h-0 rounded-lg border border-border/50 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Selected template</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{displayLabel(notionPreview?.template_label || selectedTemplate?.label, 'Executive summary')}</p>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{displayLabel(notionPreview?.template_description || selectedTemplate?.description, 'Executive handoff template')}</p>
                  {notionPreview?.page_title || notionPreview?.title ? (
                    <div className="mt-3 rounded-md bg-background/80 px-3 py-2">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Page title</p>
                      <p className="mt-1 text-xs font-medium text-foreground">{displayLabel(notionPreview.page_title || notionPreview.title, 'Executive handoff')}</p>
                    </div>
                  ) : null}
                  {Array.isArray(notionPreview?.available_templates) && notionPreview.available_templates.length ? (
                    <ScrollArea className="mt-3 h-[280px] pr-3">
                      <div className="space-y-2">
                        {notionPreview.available_templates.map((template) => (
                          <div key={template.id} className={cn(
                            'rounded-md border px-3 py-2',
                            template.id === notionPreview?.template_id ? 'border-primary/40 bg-primary/10' : 'border-border/50 bg-background/80',
                          )}>
                            <p className="text-xs font-medium text-foreground">{template.label}</p>
                            {template.description ? <p className="mt-1 text-[11px] text-muted-foreground">{template.description}</p> : null}
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  ) : null}
                </div>
                <div className="min-h-0 rounded-lg border border-border/50 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Preview sections</p>
                  <ScrollArea className="mt-3 h-[430px] pr-3">
                    <div className="space-y-3">
                      {Array.isArray(notionPreview?.preview_sections) && notionPreview.preview_sections.length ? (
                        notionPreview.preview_sections.map((section, index) => {
                          const item = section as { heading?: string; items?: string[] };
                          return (
                            <div key={`${item.heading || 'section'}-${index}`} className="rounded-md bg-background/80 px-3 py-2">
                              <p className="text-xs font-medium text-foreground">{item.heading || 'Section'}</p>
                              <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                                {(item.items || []).slice(0, 6).map((entry) => (
                                  <li key={entry} className="leading-relaxed">• {entry}</li>
                                ))}
                              </ul>
                            </div>
                          );
                        })
                      ) : (
                        <p className="text-xs text-muted-foreground">No Notion preview content is available yet.</p>
                      )}
                    </div>
                  </ScrollArea>
                </div>
              </div>
              <DialogFooter className="gap-2 sm:justify-between">
                <p className="text-[11px] text-muted-foreground">This publish action will create a Notion page using the selected template.</p>
                <div className="flex items-center gap-2">
                  {notionOpenUrl ? (
                    <Button variant="outline" onClick={() => openExternalUrl(notionOpenUrl, 'This preview does not have a published Notion page URL yet. Publish first to open it in Notion.')}>
                      Open page <ExternalLink className="ml-2 h-4 w-4" />
                    </Button>
                  ) : null}
                  <Button disabled={publishNotionMutation.isPending} onClick={() => publishNotionMutation.mutate(selectedTemplateId)}>
                    {publishNotionMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ScrollText className="mr-2 h-4 w-4" />}
                    Publish to Notion
                  </Button>
                </div>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}

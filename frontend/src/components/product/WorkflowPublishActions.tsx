import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, KanbanSquare, Loader2, ScrollText } from 'lucide-react';

import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from '@/components/ui/sonner';
import AdminOnlyFeatureCard from '@/components/access/AdminOnlyFeatureCard';
import { isAdminSession, useAuthSession } from '@/lib/auth-session';
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

type PreviewDocumentSection = {
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

const CURRENT_TRELLO_PAGE_URL = 'https://trello.com/b/FhIjewpo/mcp-actions';
const CURRENT_NOTION_PAGE_URL = 'https://apple-tsunami-1ce.notion.site/3431594b7fc080eebe5fdece0899b226?v=3431594b7fc080aca35f000cb7e0cca4&source=copy_link';

function getWorkflowTemplateOptions(workflowId: string): NotionTemplateOption[] {
  return NOTION_TEMPLATE_OPTIONS[workflowId] ?? [{ id: 'executive_summary', label: 'Executive summary', description: 'Default workflow handoff.' }];
}

function isTargetReady(status?: string | null): boolean {
  const normalized = String(status || '').trim().toLowerCase();
  return normalized === 'ready' || normalized === 'live' || normalized === 'completed' || normalized === 'success';
}

function displayLabel(value: unknown, fallback: string): string {
  const normalized = String(value || '').trim();
  if (!normalized || /^untitled/i.test(normalized)) return fallback;
  return normalized;
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

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function stripMarkdown(value: string): string {
  return value
    .replace(/^#+\s*/, '')
    .replace(/^[-*•]\s+/, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

function dedupeItems(items: string[], limit = 8): string[] {
  const seen = new Set<string>();
  const normalizedItems: string[] = [];
  for (const rawItem of items) {
    const item = stripMarkdown(rawItem);
    if (!item) continue;
    const key = item.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    normalizedItems.push(item);
    if (normalizedItems.length >= limit) break;
  }
  return normalizedItems;
}

function parseMarkdownBullets(value: string): string[] {
  return value
    .split(/\n+/)
    .map((entry) => stripMarkdown(entry))
    .filter(Boolean);
}

function parseTrelloCard(card: TrelloPreviewCard | null): { title: string; listLabel: string; summary: string | null; sections: TrelloPreviewSection[] } {
  const title = trelloPreviewFullName(card);
  const listLabel = displayLabel(card?.list_label || card?.list_name, 'Mapped list');
  const description = String(card?.description || '').replace(/\r\n/g, '\n').trim();
  const explicitSummary = stripMarkdown(String(card?.summary || ''));

  if (!description) {
    return { title, listLabel, summary: explicitSummary || null, sections: [] };
  }

  const lines = description.split('\n').map((line) => line.trim()).filter(Boolean);
  const sections: TrelloPreviewSection[] = [];
  const seenItems = new Set<string>();
  let summary: string | null = explicitSummary || null;
  let currentHeading = 'Details';
  let currentItems: string[] = [];

  const pushItem = (value: string) => {
    const normalized = stripMarkdown(value);
    if (!normalized) return;
    const key = normalized.toLowerCase();
    if (seenItems.has(key)) return;
    seenItems.add(key);
    currentItems.push(normalized);
  };

  const flushSection = () => {
    const heading = currentHeading === 'Summary' && summary ? 'Key details' : currentHeading;
    const items = dedupeItems(currentItems, 6).filter((item) => item.toLowerCase() !== String(summary || '').toLowerCase());
    if (items.length) {
      sections.push({ heading, items });
    }
    currentItems = [];
  };

  for (const line of lines) {
    const normalized = stripMarkdown(line);
    if (!normalized) continue;

    if (/^###\s+/.test(line)) {
      flushSection();
      currentHeading = normalized || 'Details';
      continue;
    }

    if (/^##+\s+/.test(line)) {
      if (!summary && normalized.toLowerCase() !== title.toLowerCase()) {
        summary = normalized || null;
      }
      continue;
    }

    if (!summary && currentHeading === 'Details') {
      summary = normalized || null;
      continue;
    }

    pushItem(normalized);
  }

  flushSection();

  let cleanedSections = sections.filter((section) => section.items.length);
  if (!cleanedSections.length) {
    const fallbackItems = dedupeItems(parseMarkdownBullets(description), 6);
    if (fallbackItems.length) {
      cleanedSections.push({ heading: 'Details', items: fallbackItems });
    }
  }

  // The real Trello checklist is rendered separately from card.checklist_items.
  // Avoid showing a duplicate Markdown-derived Suggested checklist section.
  cleanedSections = cleanedSections.filter(
    (section) => section.heading.trim().toLowerCase() !== 'suggested checklist',
  );

  return { title, listLabel, summary, sections: cleanedSections };
}

function rawTrelloLabelNames(card: TrelloPreviewCard | null): string[] {
  const labels = Array.isArray(card?.labels) ? card.labels : [];
  return labels
    .map((label) => (
      label && typeof label === 'object'
        ? stripMarkdown(String((label as { name?: unknown }).name || ''))
        : ''
    ))
    .filter(Boolean);
}

function normalizePreviewToken(value: unknown): string {
  return String(value || '').trim().toLowerCase().replace(/[\s_-]+/g, ' ');
}

function inferPreviewCategoryFromLabels(card: TrelloPreviewCard | null): string {
  const labels = rawTrelloLabelNames(card);
  const statusValue = normalizePreviewToken(card?.status || card?.list_label || card?.list_name);

  const severityValues = new Set(['critical', 'high', 'medium', 'low', 'urgent']);
  const statusValues = new Set(['open', 'review', 'needs review', 'done', 'completed', 'approved']);

  const candidate = labels.find((label) => {
    const normalized = normalizePreviewToken(label);
    if (!normalized) return false;
    if (severityValues.has(normalized)) return false;
    if (statusValues.has(normalized)) return false;
    if (statusValue && (
      normalized === statusValue ||
      normalized.includes(statusValue) ||
      statusValue.includes(normalized)
    )) return false;
    return true;
  });

  return compactText(card?.category || candidate, '', 80);
}

function extractTrelloLabelNames(card: TrelloPreviewCard | null): string[] {
  const statusValue = normalizePreviewToken(card?.status || card?.list_label || card?.list_name);
  const severityValue = normalizePreviewToken(card?.severity);
  const categoryValue = normalizePreviewToken(inferPreviewCategoryFromLabels(card));
  const duplicateValues = new Set([statusValue, severityValue, categoryValue].filter(Boolean));

  return rawTrelloLabelNames(card)
    .filter((label) => {
      const normalized = normalizePreviewToken(label);
      if (!normalized) return false;

      if (duplicateValues.has(normalized)) return false;
      if (severityValue && normalized === severityValue) return false;

      if (statusValue && (
        normalized === statusValue ||
        normalized.includes(statusValue) ||
        statusValue.includes(normalized)
      )) return false;

      if (categoryValue && (
        normalized === categoryValue ||
        normalized.includes(categoryValue) ||
        categoryValue.includes(normalized)
      )) return false;

      if (normalized === 'needs review' && statusValue.includes('review')) return false;

      return true;
    })
    .slice(0, 6);
}

function extractTrelloMetaItems(card: TrelloPreviewCard | null): Array<{ label: string; value: string }> {
  const status = compactText(card?.status || card?.list_label || card?.list_name, '', 80);
  const category = inferPreviewCategoryFromLabels(card);

  const items: Array<{ label: string; value: string | null }> = [
    { label: 'Owner', value: compactText(card?.owner, '', 80) },
    { label: 'Status', value: status },
    { label: 'Severity', value: compactText(card?.severity, '', 80) },
    { label: 'Category', value: category },
    { label: 'Due', value: compactText(card?.due, '', 80) },
  ];

  return items.filter((item): item is { label: string; value: string } => Boolean(item.value));
}


function isActionPlanTrelloCard(card: TrelloPreviewCard | null): boolean {
  if (!card) return false;

  const raw = [
    (card as Record<string, unknown>).workflow_id,
    (card as Record<string, unknown>).workflowId,
    (card as Record<string, unknown>).workflow,
    card.name,
    card.category,
    card.owner,
    card.list_label,
    card.list_name,
    ...extractTrelloLabelNames(card),
  ]
    .map((value) => String(value || '').toLowerCase())
    .join(' ');

  return raw.includes('action_plan_evidence_review')
    || raw.includes('action plan')
    || raw.includes('evidence review')
    || raw.includes('[action plan');
}


function hasPreviewEllipsis(value: unknown): boolean {
  const text = String(value || '');
  return text.includes('...') || text.includes('…');
}

function normalizePreviewTitleKey(value: unknown): string {
  return String(value || '')
    .trim()
    .replace(/[.…]+$/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

function collectPreviewFullTitles(source: unknown): string[] {
  const titles: string[] = [];
  const seen = new WeakSet<object>();

  function visit(value: unknown): void {
    if (!value || typeof value !== 'object') return;
    if (seen.has(value as object)) return;
    seen.add(value as object);

    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }

    const record = value as Record<string, unknown>;
    [
      record.full_name,
      record.fullName,
      record.full_title,
      record.fullTitle,
      record.card_title,
      record.cardTitle,
      record.action_title,
      record.actionTitle,
      record.title,
      record.name,
      record.description,
    ].forEach((candidate) => {
      const text = String(candidate || '').trim();
      if (text && !hasPreviewEllipsis(text) && text.length > 8) titles.push(text);
    });

    Object.values(record).forEach(visit);
  }

  visit(source);
  return Array.from(new Set(titles));
}

function trelloPreviewFullName(card: TrelloPreviewCard | null | undefined): string {
  if (!card) return 'Untitled card';

  const raw = card as unknown as Record<string, unknown>;
  const direct = String(
    raw.full_name
    || raw.fullName
    || raw.full_title
    || raw.fullTitle
    || raw.card_title
    || raw.cardTitle
    || raw.title
    || raw.name
    || ''
  ).trim();

  if (direct && !hasPreviewEllipsis(direct)) return direct;

  const currentKey = normalizePreviewTitleKey(direct || raw.name || raw.title);
  const candidates = collectPreviewFullTitles(card);

  const matched = candidates.find((candidate) => {
    const candidateKey = normalizePreviewTitleKey(candidate);
    return candidateKey.startsWith(currentKey) || currentKey.startsWith(candidateKey);
  });

  return matched || direct || 'Untitled card';
}


function trelloCardDisplayName(card: TrelloPreviewCard | null | undefined): string {
  if (!card) return 'Untitled card';

  const raw = card as unknown as Record<string, unknown>;
  const candidates = [
    raw.full_name,
    raw.fullName,
    raw.full_title,
    raw.fullTitle,
    raw.card_title,
    raw.cardTitle,
    raw.title,
    raw.name,
  ]
    .map((value) => String(value || '').trim())
    .filter(Boolean);

  return candidates.find(Boolean) || 'Untitled card';
}

function extractTrelloChecklistItems(card: TrelloPreviewCard | null): string[] {
  if (isActionPlanTrelloCard(card)) return [];
  const checklist = Array.isArray(card?.checklist_items) ? card.checklist_items : [];
  return dedupeItems(checklist.map((item) => String(item || '')), 6);
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

function openLocalPreviewPage(options: {
  windowTitle: string;
  badgeLabel: string;
  badgeTone?: 'trello' | 'notion';
  pageTitle: string;
  subtitle?: string | null;
  note?: string | null;
  sections: PreviewDocumentSection[];
}): void {
  const previewWindow = window.open('', '_blank');
  if (!previewWindow) {
    toast.error('The browser blocked the preview tab. Allow pop-ups for this site and try again.');
    return;
  }

  const tone = options.badgeTone === 'trello'
    ? { border: 'rgba(96,165,250,0.35)', bg: 'rgba(59,130,246,0.14)' }
    : { border: 'rgba(167,139,250,0.35)', bg: 'rgba(139,92,246,0.14)' };

  const sectionsHtml = options.sections.length
    ? options.sections.map((section) => `
        <section class="section">
          <h2>${escapeHtml(section.heading)}</h2>
          <ul>
            ${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
        </section>
      `).join('')
    : '<section class="section"><p class="empty">No preview content is available yet.</p></section>';

  previewWindow.document.open();
  previewWindow.document.write(`<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(options.windowTitle)}</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #020817;
        --panel: rgba(15, 23, 42, 0.92);
        --panel-strong: rgba(15, 23, 42, 0.98);
        --border: rgba(148, 163, 184, 0.18);
        --text: #e5eefc;
        --muted: #9fb0cf;
        --accent-border: ${tone.border};
        --accent-bg: ${tone.bg};
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        background: radial-gradient(circle at top, rgba(30, 64, 175, 0.24), transparent 32%), var(--bg);
        color: var(--text);
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      .shell {
        width: min(980px, calc(100vw - 32px));
        margin: 24px auto;
        padding: 28px;
        border-radius: 24px;
        background: var(--panel);
        border: 1px solid var(--border);
        box-shadow: 0 32px 80px rgba(2, 6, 23, 0.55);
      }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        border: 1px solid var(--accent-border);
        background: var(--accent-bg);
        color: var(--text);
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      h1 {
        margin: 18px 0 8px;
        font-size: clamp(28px, 4vw, 40px);
        line-height: 1.1;
      }
      .subtitle {
        margin: 0;
        color: var(--muted);
        font-size: 16px;
        line-height: 1.7;
      }
      .note {
        margin-top: 18px;
        padding: 14px 16px;
        border-radius: 16px;
        border: 1px solid var(--accent-border);
        background: rgba(15, 23, 42, 0.68);
        color: var(--muted);
        font-size: 14px;
        line-height: 1.7;
      }
      .grid {
        display: grid;
        gap: 16px;
        margin-top: 22px;
      }
      .section {
        padding: 18px 18px 16px;
        border-radius: 18px;
        background: var(--panel-strong);
        border: 1px solid var(--border);
      }
      .section h2 {
        margin: 0 0 12px;
        font-size: 16px;
      }
      .section ul {
        margin: 0;
        padding-left: 18px;
        color: var(--muted);
      }
      .section li {
        margin: 8px 0;
        line-height: 1.7;
      }
      .empty {
        margin: 0;
        color: var(--muted);
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <div class="badge">${escapeHtml(options.badgeLabel)}</div>
      <h1>${escapeHtml(options.pageTitle)}</h1>
      ${options.subtitle ? `<p class="subtitle">${escapeHtml(options.subtitle)}</p>` : ''}
      ${options.note ? `<div class="note">${escapeHtml(options.note)}</div>` : ''}
      <div class="grid">${sectionsHtml}</div>
    </main>
  </body>
</html>`);
  previewWindow.document.close();
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
  const { data: authSession } = useAuthSession();
  const canPublishExternal = isAdminSession(authSession);
  const isAdmin = canPublishExternal;
  const [dialogTarget, setDialogTarget] = useState<PreviewTarget>(null);
  const [showTrelloPublishBlockedCard, setShowTrelloPublishBlockedCard] = useState(false);
  const [showNotionPublishBlockedCard, setShowNotionPublishBlockedCard] = useState(false);
  const templateOptions = useMemo(() => getWorkflowTemplateOptions(workflowId), [workflowId]);
  const [selectedTemplateId, setSelectedTemplateId] = useState(templateOptions[0]?.id ?? 'executive_summary');
  const [selectedTrelloCardIndex, setSelectedTrelloCardIndex] = useState(0);
  const [trelloPreview, setTrelloPreview] = useState<ProductPublishTrelloResponse | null>(null);
  const [notionPreview, setNotionPreview] = useState<ProductPublishNotionResponse | null>(null);
  const [lastPublishedTrelloPayload, setLastPublishedTrelloPayload] = useState<ProductPublishTrelloResponse | null>(null);
  const [lastPublishedNotionPayload, setLastPublishedNotionPayload] = useState<ProductPublishNotionResponse | null>(null);

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
      setShowTrelloPublishBlockedCard(false);
      setDialogTarget('trello');
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Trello preview failed.'),
  });

  const publishTrelloMutation = useMutation({
    mutationFn: async () => {
      if (!result) throw new Error('Run the workflow before publishing to Trello.');
      return publishProductWorkflowToTrello(result, {
        runId,
        dryRun: false,
        previewPayload: notionPreviewPayload ?? undefined,
        selectedCardIndex: selectedTrelloCardIndex,
      });
    },
    onSuccess: async (payload) => {
      await refreshProductQueries();
      setLastPublishedTrelloPayload(payload);
      setTrelloPreview(payload);
      setDialogTarget('trello');
      onTrelloPublished?.(payload);
      toast.success(payload.message || 'Published to Trello. You can open the created page now.');
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
      if (payload.template_id) setSelectedTemplateId(String(payload.template_id));
      setNotionPreview(payload);
      setShowNotionPublishBlockedCard(false);
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
      if (payload.template_id) setSelectedTemplateId(String(payload.template_id));
      setLastPublishedNotionPayload(payload);
      setNotionPreview(payload);
      setDialogTarget('notion');
      onNotionPublished?.(payload);
      toast.success(payload.message || 'Published to Notion. You can open the created page now.');
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
    lastPublishedTrelloPayload?.board_url
    || (Array.isArray(lastPublishedTrelloPayload?.created_card_urls) ? lastPublishedTrelloPayload?.created_card_urls?.[0] : null)
    || buildTrelloBoardFallbackUrl(lastPublishedTrelloPayload?.target_board_id),
  ), [lastPublishedTrelloPayload]);
  const notionOpenUrl = useMemo(() => normalizeExternalUrl(lastPublishedNotionPayload?.page_url), [lastPublishedNotionPayload]);
  const canOpenPublishedTrelloPage = !(lastPublishedTrelloPayload?.dry_run ?? true) && Boolean(trelloOpenUrl);
  const canOpenPublishedNotionPage = !(lastPublishedNotionPayload?.dry_run ?? true) && Boolean(notionOpenUrl);
  const availableNotionTemplates = useMemo(() => {
    if (Array.isArray(notionPreview?.available_templates) && notionPreview.available_templates.length) {
      return notionPreview.available_templates.map((template) => ({
        id: String(template.id),
        label: displayLabel(template.label, 'Template'),
        description: compactText(template.description, '', 120),
      }));
    }
    return templateOptions;
  }, [notionPreview?.available_templates, templateOptions]);

  useEffect(() => {
    if (dialogTarget === 'trello') {
      setSelectedTrelloCardIndex(0);
    }
  }, [dialogTarget, trelloPreview?.planned_card_count]);


  useEffect(() => {
    setTrelloPreview(null);
    setNotionPreview(null);
    setLastPublishedTrelloPayload(null);
    setLastPublishedNotionPayload(null);
    setDialogTarget(null);
  }, [workflowId, runId]);

  const openTrelloPage = () => {
    openExternalUrl(trelloOpenUrl, 'Publish to Trello first to open the created card or board.');
  };

  const openNotionPage = () => {
    openExternalUrl(notionOpenUrl, 'Publish to Notion first to open the created page.');
  };

  const openCurrentTrelloPage = () => {
    openExternalUrl(CURRENT_TRELLO_PAGE_URL, 'The current Trello board URL is not configured.');
  };

  const openCurrentNotionPage = () => {
    openExternalUrl(CURRENT_NOTION_PAGE_URL, 'The current Notion database URL is not configured.');
  };

  const handlePublishTrello = () => {
    if (!canPublishExternal) {
      setShowTrelloPublishBlockedCard(true);
      toast.error('Publishing to Trello requires Admin Mode. You can still preview the card and open the current board.');
      return;
    }
    publishTrelloMutation.mutate();
  };

  const handlePublishNotion = () => {
    if (!canPublishExternal) {
      setShowNotionPublishBlockedCard(true);
      toast.error('Publishing to Notion requires Admin Mode. You can still preview the handoff and open the current database.');
      return;
    }
    publishNotionMutation.mutate(selectedTemplateId);
  };

  const renderPublishBlockedOverlay = (
    platform: 'trello' | 'notion',
    onClose: () => void,
  ) => {
    const isTrello = platform === 'trello';

    return (
      <div className="absolute inset-0 z-[80] flex items-center justify-center rounded-2xl bg-slate-950/75 p-6 backdrop-blur-sm">
        <div className="w-full max-w-xl">
          <AdminOnlyFeatureCard
            eyebrow="Public preview mode"
            title={isTrello ? 'Publishing to Trello requires Admin Mode' : 'Publishing to Notion requires Admin Mode'}
            description={
              isTrello
                ? 'Visitors can inspect the planned Trello card and open the current board, but creating or updating live cards is limited to Admin Mode.'
                : 'Visitors can inspect the planned Notion handoff and open the current database, but creating live pages is limited to Admin Mode.'
            }
            valuePoints={
              isTrello
                ? [
                    'Preview the selected card before anything is sent.',
                    'Open the current Trello board to see the live public workspace.',
                    'Connect with Danyel for a guided demo using your own operations board.',
                  ]
                : [
                    'Preview the page structure before anything is sent.',
                    'Open the current Notion database to see the live public workspace.',
                    'Connect with Danyel for a guided demo using your own executive handoff format.',
                  ]
            }
            secondaryLabel="Want to test this with your own workspace?"
            secondaryText={
              isTrello
                ? 'Connect with Danyel and we can run a guided demo using your own operations board and workflow handoff.'
                : 'Connect with Danyel and we can run a guided demo using your own Notion database and handoff format.'
            }
            ctaLabel="Connect with Danyel on LinkedIn"
            ctaHref="https://www.linkedin.com/in/danyel-"
          />
          <div className="mt-4 flex justify-center">
            <Button type="button" variant="outline" onClick={onClose}>
              Keep exploring preview
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const externalPublishAdminOnlyCard = (
    <AdminOnlyFeatureCard
      eyebrow="Admin-only delivery"
      title="External publishing is protected"
      description="You can explore workflow results in the public demo, but creating or updating live Trello cards and Notion pages requires Admin Mode because it sends data to external workspaces."
      valuePoints={[
        'Preview how delivery handoffs fit your workflow.',
        'Connect Trello, Notion, or your preferred operations tools in a guided demo.',
        'Protect shared demo integrations while still showing the delivery loop.',
      ]}
      secondaryLabel="Want to see the full delivery loop?"
      secondaryText="Connect with Danyel and we can run a private demo using your board, workspace, workflow output, and handoff format."
      compact
    />
  );

  if (false && !isAdmin) {
    return (
      <div className={className} data-testid="workflow-publish-actions">
        {externalPublishAdminOnlyCard}
      </div>
    );
  }

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
      </GlassCard>

      <Dialog open={dialogTarget !== null} onOpenChange={(open) => !open && setDialogTarget(null)}>
        <DialogContent className="fixed left-1/2 top-1/2 z-50 flex max-h-[86vh] w-[calc(100vw-2rem)] max-w-5xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl border-border/60 bg-background/95 shadow-2xl sm:max-w-5xl">
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
              <div className="grid min-h-0 flex-1 gap-4 py-2 md:grid-cols-[0.92fr_1.08fr]">
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
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Card queue</p>
                        <p className="mt-1 text-[11px] text-muted-foreground">Pick a card to inspect its details.</p>
                      </div>
                      <Badge variant="outline" className="text-[10px]">{trelloCards.length} item(s)</Badge>
                    </div>
                    <ScrollArea className="mt-3 h-[34vh] max-h-[360px] pr-3">
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
                                isActive ? 'border-primary/50 bg-primary/10 shadow-[0_0_0_1px_rgba(59,130,246,0.12)]' : 'border-border/50 bg-background/80 hover:border-primary/20 hover:bg-background',
                              )}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <p className="text-xs font-medium leading-relaxed text-foreground whitespace-normal break-words">{parsed.title}</p>
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

                <div className="flex min-h-0 overflow-hidden flex-col rounded-lg border border-border/50 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Card preview</p>
                  {activeTrelloCard ? (
                    <>
                      <div className="mt-3 rounded-md bg-background/80 px-3 py-3">
                        <p className="text-sm font-medium leading-relaxed text-foreground whitespace-normal break-words">{parsedActiveTrelloCard.title}</p>
                        <p className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">{parsedActiveTrelloCard.listLabel}</p>
                        {parsedActiveTrelloCard.summary ? <p className="mt-3 text-[12px] leading-relaxed text-muted-foreground">{parsedActiveTrelloCard.summary}</p> : null}
                        {extractTrelloLabelNames(activeTrelloCard).length ? (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {extractTrelloLabelNames(activeTrelloCard).map((label) => (
                              <Badge key={label} variant="outline" className="text-[10px]">{label}</Badge>
                            ))}
                          </div>
                        ) : null}
                        {extractTrelloMetaItems(activeTrelloCard).length ? (
                          <div className="mt-3 grid gap-2 sm:grid-cols-2">
                            {extractTrelloMetaItems(activeTrelloCard).map((item) => (
                              <div key={`${item.label}-${item.value}`} className="rounded-md border border-border/40 bg-secondary/20 px-2 py-2">
                                <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{item.label}</div>
                                <div className="mt-1 text-xs text-foreground">{item.value}</div>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                      <ScrollArea className="mt-3 h-[46vh] max-h-[430px] pr-3">
                        <div className="space-y-3">
                          {parsedActiveTrelloCard.sections.map((section) => (
                            <div key={section.heading} className="rounded-md bg-background/80 px-3 py-2">
                              <p className="text-xs font-medium text-foreground">{section.heading}</p>
                              <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                                {section.items.map((item) => <li key={item} className="leading-relaxed">• {item}</li>)}
                              </ul>
                            </div>
                          ))}
                          {!isActionPlanTrelloCard(activeTrelloCard) && extractTrelloChecklistItems(activeTrelloCard).length ? (
                            <div className="rounded-md bg-background/80 px-3 py-2">
                              <p className="text-xs font-medium text-foreground">Suggested checklist</p>
                              <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                                {extractTrelloChecklistItems(activeTrelloCard).map((item) => <li key={item} className="leading-relaxed">• {item}</li>)}
                              </ul>
                            </div>
                          ) : null}
                        </div>
                      </ScrollArea>
                    </>
                  ) : <p className="mt-3 text-xs text-muted-foreground">Select a planned card to inspect the publish preview.</p>}
                </div>
              </div>
              <DialogFooter className="mt-2 shrink-0 gap-2 border-t border-border/40 pt-3 sm:justify-between">
                <p className="text-[11px] text-muted-foreground">
                  {canOpenPublishedTrelloPage
                    ? 'Published. You can reopen the created Trello page from here.'
                    : 'Preview only. Nothing is created in Trello until you click “Publish selected card”.'}
                </p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" onClick={openCurrentTrelloPage}>
                    Open current Trello page <ExternalLink className="ml-2 h-4 w-4" />
                  </Button>
                  <Button disabled={publishTrelloMutation.isPending} onClick={handlePublishTrello}>
                    {publishTrelloMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KanbanSquare className="mr-2 h-4 w-4" />}
                    {trelloCards.length ? `Publish selected card${trelloCards.length > 1 ? ` (#${selectedTrelloCardIndex + 1})` : ""}` : "Publish to Trello"}
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
              <div className="grid min-h-0 flex-1 overflow-hidden gap-4 py-2 md:grid-cols-[0.82fr_1.18fr]">
                <div className="flex min-h-0 overflow-hidden flex-col rounded-lg border border-border/50 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Selected template</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{displayLabel(notionPreview?.template_label || selectedTemplate?.label, 'Executive summary')}</p>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{displayLabel(notionPreview?.template_description || selectedTemplate?.description, 'Executive handoff template')}</p>
                  {notionPreview?.page_title || notionPreview?.title ? (
                    <div className="mt-3 rounded-md bg-background/80 px-3 py-2">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Page title</p>
                      <p className="mt-1 text-xs font-medium text-foreground">{displayLabel(notionPreview.page_title || notionPreview.title, 'Executive handoff')}</p>
                    </div>
                  ) : null}
                  <ScrollArea className="mt-3 h-[36vh] max-h-[320px] pr-3">
                    <div className="space-y-2">
                      {availableNotionTemplates.map((template) => {
                        const isActive = template.id === (notionPreview?.template_id || selectedTemplateId);
                        return (
                          <button
                            key={template.id}
                            type="button"
                            disabled={previewNotionMutation.isPending || publishNotionMutation.isPending}
                            onClick={() => {
                              setSelectedTemplateId(template.id);
                              previewNotionMutation.mutate(template.id);
                            }}
                            className={cn(
                              'w-full rounded-md border px-3 py-3 text-left transition-colors',
                              isActive ? 'border-primary/50 bg-primary/10 shadow-[0_0_0_1px_rgba(59,130,246,0.12)]' : 'border-border/50 bg-background/80 hover:border-primary/20 hover:bg-background',
                            )}
                          >
                            <p className="text-xs font-medium text-foreground">{template.label}</p>
                            {template.description ? <p className="mt-1 text-[11px] text-muted-foreground">{template.description}</p> : null}
                          </button>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </div>
                <div className="flex min-h-0 overflow-hidden flex-col rounded-lg border border-border/50 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Preview sections</p>
                  <ScrollArea className="mt-3 h-[46vh] max-h-[430px] pr-3">
                    <div className="space-y-3">
                      {Array.isArray(notionPreview?.preview_sections) && notionPreview.preview_sections.length ? (
                        notionPreview.preview_sections.map((section, index) => {
                          const item = section as { heading?: string; items?: string[] };
                          return (
                            <div key={`${item.heading || 'section'}-${index}`} className="rounded-md bg-background/80 px-3 py-2">
                              <p className="text-xs font-medium text-foreground">{displayLabel(item.heading, 'Section')}</p>
                              <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                                {dedupeItems(Array.isArray(item.items) ? item.items : [], 8).map((entry) => (
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
              <DialogFooter className="mt-2 shrink-0 gap-2 border-t border-border/40 pt-3 sm:justify-between">
                <p className="text-[11px] text-muted-foreground">
                  {canOpenPublishedNotionPage
                    ? 'Published. You can reopen the created Notion page from here.'
                    : 'Preview only. Nothing is created in Notion until you click “Publish to Notion”.'}
                </p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" onClick={openCurrentNotionPage}>
                    Open current Notion page <ExternalLink className="ml-2 h-4 w-4" />
                  </Button>
                  <Button disabled={publishNotionMutation.isPending} onClick={handlePublishNotion}>
                    {publishNotionMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ScrollText className="mr-2 h-4 w-4" />}
                    Publish to Notion
                  </Button>
                </div>
              </DialogFooter>
            </>
          ) : null}
          {dialogTarget === 'trello' && showTrelloPublishBlockedCard
            ? renderPublishBlockedOverlay('trello', () => setShowTrelloPublishBlockedCard(false))
            : null}
          {dialogTarget === 'notion' && showNotionPublishBlockedCard
            ? renderPublishBlockedOverlay('notion', () => setShowNotionPublishBlockedCard(false))
            : null}
        </DialogContent>
      </Dialog>
    </>
  );
}

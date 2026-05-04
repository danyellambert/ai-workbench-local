import { motion } from 'framer-motion';
import { Fragment, KeyboardEvent, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Send, FileText, Sparkles, AlertTriangle, Loader2, FolderClock, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { GlassCard } from '@/components/shared/ui-components';
import { aiLabQueryKeys, createLabChatSession, deleteLabChatSession, getLabChatPage, sendLabChatMessage } from '@/lib/ai-lab-data';
import { getProductDocumentLibrary, type ProductDocumentLibraryEntry } from '@/lib/product-api';
import type { LabChatMessage, LabChatMessageSource, LabChatPageData, LabChatSessionSummary, LabDocumentOption, LabTimelineEntry } from '@/lib/ai-lab-data';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAppStore } from '@/lib/store';

const CHAT_INPUT_MAX_CHARS = 2000;

function prettifyMetricLabel(label: string) {
  return label
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatMetricValue(value: unknown): string {
  if (value == null || value === '') {
    return '—';
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      return '—';
    }
    if (value > 0 && value <= 1) {
      return `${Math.round(value * 100)}%`;
    }
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (Array.isArray(value)) {
    return value.map((entry) => formatMetricValue(entry)).join(', ');
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, entryValue]) => `${prettifyMetricLabel(key)}: ${formatMetricValue(entryValue)}`)
      .join(' · ');
  }
  return String(value);
}

function normalizeRows(rows: unknown) {
  if (Array.isArray(rows)) {
    return rows.flatMap((row, index) => {
      if (!row || typeof row !== 'object') {
        return [];
      }
      const record = row as Record<string, unknown>;
      return [
        {
          label: typeof record.label === 'string' ? record.label : `Metric ${index + 1}`,
          value: formatMetricValue(record.value),
        },
      ];
    });
  }

  if (rows && typeof rows === 'object') {
    return Object.entries(rows as Record<string, unknown>).map(([key, value]) => ({
      label: prettifyMetricLabel(key),
      value: formatMetricValue(value),
    }));
  }

  return [];
}

function normalizeMessageSources(sources: unknown): LabChatMessageSource[] {
  if (!Array.isArray(sources)) {
    return [];
  }

  return sources.flatMap((source, index) => {
    if (!source || typeof source !== 'object') {
      return [];
    }

    const record = source as Record<string, unknown>;
    const rawScore = typeof record.score === 'number' ? record.score : null;
    const rawScoreKind =
      typeof record.score_kind === 'string'
        ? record.score_kind
        : typeof record.scoreKind === 'string'
          ? record.scoreKind
          : null;
    const rawScoreLabel =
      typeof record.score_label === 'string'
        ? record.score_label
        : typeof record.scoreLabel === 'string'
          ? record.scoreLabel
          : null;

    return [
      {
        label:
          typeof record.label === 'string'
            ? record.label
            : typeof record.doc === 'string'
              ? record.doc
              : typeof record.title === 'string'
                ? record.title
                : `Source ${index + 1}`,
        detail:
          typeof record.detail === 'string'
            ? record.detail
            : typeof record.chunk === 'string'
              ? record.chunk
              : typeof record.path === 'string'
                ? record.path
                : null,
        score: rawScore == null ? null : rawScore <= 1 ? rawScore * 100 : rawScore,
        scoreKind: rawScoreKind,
        scoreLabel: rawScoreLabel,
      },
    ];
  });
}


function renderInlineMarkdown(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+?\*\*)/g).map((segment, index) => {
    const boldMatch = segment.match(/^\*\*(.+?)\*\*$/);
    if (boldMatch) {
      return (
        <strong key={`bold-${index}`} className="font-semibold text-foreground">
          {boldMatch[1]}
        </strong>
      );
    }

    return <Fragment key={`text-${index}`}>{segment}</Fragment>;
  });
}

function normalizeMarkdownLine(line: string) {
  return line.trim().replace(/^[-•]\s+/, '');
}

function isStructuredChatBlock(lines: string[]) {
  return lines.some((line) =>
    /\*\*(Action|Owner role|Timing\/due date|Evidence|Priority|Control gap|Risk\/impact|Suggested mitigation|Risky|Unsupported|Contradictory|Verify next):\*\*/i.test(line),
  );
}

function renderMessageBlock(block: string, blockIndex: number): ReactNode {
  const lines = block
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return null;
  }

  if (isStructuredChatBlock(lines)) {
    return (
      <div key={`block-${blockIndex}`} className="rounded-lg border border-border/30 bg-background/20 px-3 py-2 space-y-1.5">
        {lines.map((line, lineIndex) => (
          <p key={`block-${blockIndex}-line-${lineIndex}`} className="text-xs leading-relaxed">
            {renderInlineMarkdown(normalizeMarkdownLine(line))}
          </p>
        ))}
      </div>
    );
  }

  if (lines.every((line) => /^[-•]\s+/.test(line))) {
    return (
      <ul key={`block-${blockIndex}`} className="list-disc pl-4 space-y-1">
        {lines.map((line, lineIndex) => (
          <li key={`block-${blockIndex}-item-${lineIndex}`} className="text-xs leading-relaxed">
            {renderInlineMarkdown(normalizeMarkdownLine(line))}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div key={`block-${blockIndex}`} className="space-y-1.5">
      {lines.map((line, lineIndex) => (
        <p key={`block-${blockIndex}-p-${lineIndex}`} className="text-xs leading-relaxed">
          {renderInlineMarkdown(line)}
        </p>
      ))}
    </div>
  );
}

function renderMessageContent(content: string) {
  const blocks = String(content || '')
    .split(/\n\s*\n/g)
    .map((block) => block.trim())
    .filter(Boolean);

  if (!blocks.length) {
    return null;
  }

  return <div className="space-y-3">{blocks.map((block, index) => renderMessageBlock(block, index))}</div>;
}


function normalizeMessages(messages: unknown): LabChatMessage[] {
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages.flatMap((message, index) => {
    if (!message || typeof message !== 'object') {
      return [];
    }

    const record = message as Record<string, unknown>;
    return [
      {
        id: typeof record.id === 'string' ? record.id : `message-${index + 1}`,
        role: record.role === 'user' ? 'user' : 'assistant',
        content: typeof record.content === 'string' ? record.content : '',
        timestamp: typeof record.timestamp === 'string' ? record.timestamp : null,
        sources: normalizeMessageSources(record.sources),
      },
    ];
  });
}

function normalizeSessions(sessions: unknown): LabChatSessionSummary[] {
  if (!Array.isArray(sessions)) {
    return [];
  }

  return sessions.flatMap((session, index) => {
    if (!session || typeof session !== 'object') {
      return [];
    }

    const record = session as Record<string, unknown>;
    const sessionId =
      typeof record.session_id === 'string'
        ? record.session_id
        : typeof record.id === 'string'
          ? record.id
          : `session-${index + 1}`;

    return [
      {
        session_id: sessionId,
        title:
          typeof record.title === 'string'
            ? record.title
            : typeof record.name === 'string'
              ? record.name
              : `Session ${index + 1}`,
        updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
        message_count:
          typeof record.message_count === 'number'
            ? record.message_count
            : typeof record.messages_count === 'number'
              ? record.messages_count
              : typeof record.messageCount === 'number'
                ? record.messageCount
                : 0,
        status: typeof record.status === 'string' ? record.status : null,
        document_count:
          typeof record.document_count === 'number'
            ? record.document_count
            : typeof record.documentCount === 'number'
              ? record.documentCount
              : 0,
        last_error:
          typeof record.last_error === 'string'
            ? record.last_error
            : typeof record.lastError === 'string'
              ? record.lastError
              : null,
        last_model:
          typeof record.last_model === 'string'
            ? record.last_model
            : typeof record.lastModel === 'string'
              ? record.lastModel
              : null,
        avg_latency_s:
          typeof record.avg_latency_s === 'number'
            ? record.avg_latency_s
            : typeof record.avgLatencyS === 'number'
              ? record.avgLatencyS
              : null,
        grounded_messages:
          typeof record.grounded_messages === 'number'
            ? record.grounded_messages
            : typeof record.groundedMessages === 'number'
              ? record.groundedMessages
              : 0,
      },
    ];
  });
}

function normalizeDocuments(documents: unknown): LabDocumentOption[] {
  if (!Array.isArray(documents)) {
    return [];
  }

  return documents.flatMap((document, index) => {
    if (!document || typeof document !== 'object') {
      return [];
    }

    const record = document as Record<string, unknown>;
    const documentId =
      typeof record.document_id === 'string'
        ? record.document_id
        : typeof record.id === 'string'
          ? record.id
          : `document-${index + 1}`;

    return [
      {
        document_id: documentId,
        name:
          typeof record.name === 'string'
            ? record.name
            : typeof record.title === 'string'
              ? record.title
              : `Document ${index + 1}`,
        status: typeof record.status === 'string' ? record.status : 'indexed',
        chunk_count: typeof record.chunk_count === 'number' ? record.chunk_count : typeof record.chunkCount === 'number' ? record.chunkCount : undefined,
        char_count: typeof record.char_count === 'number' ? record.char_count : typeof record.charCount === 'number' ? record.charCount : undefined,
        indexed_at: typeof record.indexed_at === 'string' ? record.indexed_at : typeof record.indexedAt === 'string' ? record.indexedAt : null,
        loader_strategy_label: typeof record.loader_strategy_label === 'string' ? record.loader_strategy_label : typeof record.loaderStrategyLabel === 'string' ? record.loaderStrategyLabel : null,
        size_bytes: typeof record.size_bytes === 'number' ? record.size_bytes : typeof record.sizeBytes === 'number' ? record.sizeBytes : null,
        size_label: typeof record.size_label === 'string' ? record.size_label : typeof record.sizeLabel === 'string' ? record.sizeLabel : null,
        source_type: typeof record.source_type === 'string' ? record.source_type : typeof record.sourceType === 'string' ? record.sourceType : null,
        page_count: typeof record.page_count === 'number' ? record.page_count : typeof record.pageCount === 'number' ? record.pageCount : null,
        warnings: Array.isArray(record.warnings) ? record.warnings.filter((warning): warning is string => typeof warning === 'string') : [],
      },
    ];
  });
}

function productDocumentToLabOption(document: ProductDocumentLibraryEntry): LabDocumentOption {
  return {
    document_id: document.document_id,
    name: document.name,
    status: document.status,
    chunk_count: document.chunk_count,
    char_count: document.char_count,
    indexed_at: document.indexed_at ?? null,
    loader_strategy_label: document.loader_strategy_label ?? null,
    size_bytes: document.size_bytes ?? null,
    size_label: document.size_label ?? null,
    source_type: document.source_type ?? null,
    page_count: document.page_count ?? null,
    warnings: document.warnings ?? [],
  };
}

function mergeDocumentOptions(primary: LabDocumentOption[], secondary: LabDocumentOption[]): LabDocumentOption[] {
  const byId = new Map<string, LabDocumentOption>();
  for (const document of [...primary, ...secondary]) {
    if (!document.document_id || byId.has(document.document_id)) continue;
    byId.set(document.document_id, document);
  }
  return Array.from(byId.values());
}

function removeSessionFromPage(page: unknown, deletedSessionId: string): LabChatPageData | unknown {
  if (!page || typeof page !== 'object') {
    return page;
  }

  const chatPage = page as LabChatPageData;
  const nextSessions = Array.isArray(chatPage.sessions)
    ? chatPage.sessions.filter((session) => session.session_id !== deletedSessionId)
    : [];
  const activeWasDeleted = chatPage.active_session_id === deletedSessionId;
  const nextActiveSessionId = activeWasDeleted ? (nextSessions[0]?.session_id ?? null) : chatPage.active_session_id;
  const nextActiveSession = nextSessions.find((session) => session.session_id === nextActiveSessionId) ?? nextSessions[0] ?? null;

  return {
    ...chatPage,
    sessions: nextSessions,
    active_session_id: nextActiveSessionId,
    active_session: nextActiveSession,
    messages: activeWasDeleted ? [] : chatPage.messages,
  };
}

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [documentPickerOpen, setDocumentPickerOpen] = useState(false);
  const [documentFilter, setDocumentFilter] = useState('');
  const [draftDocumentIds, setDraftDocumentIds] = useState<string[]>([]);
  const operatorPreferences = useAppStore((state) => state.operatorPreferences);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: aiLabQueryKeys.chat(sessionId),
    queryFn: () => getLabChatPage(sessionId),
    retry: false,
    refetchOnWindowFocus: false,
  });

  const productDocumentLibraryQuery = useQuery({
    queryKey: ['product-document-library'],
    queryFn: getProductDocumentLibrary,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  useEffect(() => {
    if (data?.active_session_id && data.active_session_id !== sessionId) {
      setSessionId(data.active_session_id);
    }
  }, [data?.active_session_id, sessionId]);

  const serverSelectedDocuments = useMemo(() => normalizeDocuments(data?.selected_documents), [data?.selected_documents]);
  const productAvailableDocuments = useMemo(
    () => (productDocumentLibraryQuery.data?.documents ?? [])
      .filter((document) => document.status === 'indexed' || document.status === 'warning')
      .map(productDocumentToLabOption),
    [productDocumentLibraryQuery.data?.documents],
  );
  const availableDocuments = useMemo(() => {
    const pageAvailableDocuments = normalizeDocuments((data as { available_documents?: unknown } | undefined)?.available_documents ?? data?.selected_documents);
    return mergeDocumentOptions(productAvailableDocuments, pageAvailableDocuments);
  }, [data, productAvailableDocuments]);
  const serverSelectedDocumentIds = useMemo(
    () => serverSelectedDocuments.map((document) => document.document_id).filter(Boolean),
    [serverSelectedDocuments],
  );
  const messages = useMemo(() => normalizeMessages(data?.messages), [data?.messages]);
  const sessions = useMemo(() => normalizeSessions(data?.sessions), [data?.sessions]);
  const sessionTimeline = useMemo<LabTimelineEntry[]>(() => (Array.isArray(data?.session_timeline) ? data.session_timeline as LabTimelineEntry[] : []), [data?.session_timeline]);

  useEffect(() => {
    const availableSet = new Set(availableDocuments.map((document) => document.document_id));
    const nextSelection = serverSelectedDocumentIds.filter((documentId) => availableSet.has(documentId));
    setDraftDocumentIds((current) => {
      const currentKey = current.join('|');
      const nextKey = nextSelection.join('|');
      return currentKey === nextKey ? current : nextSelection;
    });
  }, [sessionId, availableDocuments, serverSelectedDocumentIds]);

  const selectedDocumentIds = draftDocumentIds;
  const selectedDocuments = useMemo(
    () => availableDocuments.filter((document) => selectedDocumentIds.includes(document.document_id)),
    [availableDocuments, selectedDocumentIds],
  );
  const filteredAvailableDocuments = useMemo(() => {
    const normalizedFilter = documentFilter.trim().toLowerCase();
    if (!normalizedFilter) {
      return availableDocuments;
    }
    return availableDocuments.filter((document) => {
      const haystack = [document.name, document.status, document.loader_strategy_label, document.source_type]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(normalizedFilter);
    });
  }, [availableDocuments, documentFilter]);

  const sendMutation = useMutation({
    mutationFn: async (contentOverride?: string) => {
      const content = (typeof contentOverride === 'string' ? contentOverride : input).trim();
      if (!content) {
        throw new Error('Message content is required.');
      }
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const created = await createLabChatSession({ document_ids: selectedDocumentIds });
        activeSessionId = created.page.active_session_id ?? created.session.session_id;
      }
      const response = await sendLabChatMessage(activeSessionId, {
        content,
        document_ids: selectedDocumentIds,
      });
      return {
        response,
        activeSessionId: response.page.active_session_id ?? activeSessionId,
      };
    },
    onSuccess: ({ response, activeSessionId }) => {
      setSessionId(activeSessionId);
      setInput('');
      queryClient.setQueryData(aiLabQueryKeys.chat(activeSessionId), response.page);
      queryClient.invalidateQueries({ queryKey: ['ai-lab', 'chat'] });
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.artifacts });
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.runtime });
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.overview });
    },
  });

  const createSessionMutation = useMutation({
    mutationFn: async () => createLabChatSession({ document_ids: selectedDocumentIds }),
    onSuccess: (response) => {
      const nextSessionId = response.page.active_session_id ?? response.session.session_id;
      setSessionId(nextSessionId);
      queryClient.setQueryData(aiLabQueryKeys.chat(nextSessionId), response.page);
      queryClient.invalidateQueries({ queryKey: ['ai-lab', 'chat'] });
    },
  });

  const deleteSessionMutation = useMutation({
    mutationFn: async (targetSessionId: string) => deleteLabChatSession(targetSessionId),
    onMutate: async (targetSessionId) => {
      await queryClient.cancelQueries({ queryKey: ['ai-lab', 'chat'] });
      setSessionId((current) => (current === targetSessionId ? null : current));
      queryClient.setQueriesData({ queryKey: ['ai-lab', 'chat'] }, (cachedPage) => removeSessionFromPage(cachedPage, targetSessionId));
    },
    onSuccess: (response, deletedSessionId) => {
      const nextSessionId = response.page.active_session_id ?? null;
      setSessionId((current) => (current === deletedSessionId || current === null ? nextSessionId : current));
      queryClient.setQueryData(aiLabQueryKeys.chat(nextSessionId), response.page);
      queryClient.invalidateQueries({ queryKey: ['ai-lab', 'chat'] });
    },
    onError: (_error, deletedSessionId) => {
      queryClient.setQueriesData({ queryKey: ['ai-lab', 'chat'] }, (cachedPage) => removeSessionFromPage(cachedPage, deletedSessionId));
      setSessionId((current) => (current === deletedSessionId ? null : current));
      queryClient.invalidateQueries({ queryKey: ['ai-lab', 'chat'] });
    },
  });

  const hasVisibleRuntimeError = isError || sendMutation.isError;
  const activeSessionId = data?.active_session_id ?? sessionId ?? sessions[0]?.session_id ?? null;
  const activeSession = sessions.find((item) => item.session_id === activeSessionId) ?? sessions[0];
  const activeSessionError = activeSession?.last_error?.trim() ?? null;
  const showActiveSessionError = Boolean(activeSessionError && !/^HTTP Error\s+\d+:/i.test(activeSessionError));
  const effectiveStatus = data?.status === 'degraded' && !hasVisibleRuntimeError ? 'live' : data?.status;
  const activeStatusLabel = effectiveStatus === 'degraded' ? 'Degraded' : effectiveStatus === 'trace_only' ? 'Trace only' : 'Live';
  const canSend = availableDocuments.length > 0 && selectedDocumentIds.length > 0;
  const sendDisabledReason = availableDocuments.length === 0
    ? data?.capabilities?.reason ?? 'At least one indexed document is required to send grounded AI LAB chat messages.'
    : selectedDocumentIds.length === 0
      ? 'Select at least one document to ground the next turn.'
      : null;

  const handleSend = async (contentOverride?: string) => {
    const content = (typeof contentOverride === 'string' ? contentOverride : input).trim();
    if (!canSend || sendMutation.isPending || !content) {
      return;
    }
    await sendMutation.mutateAsync(content);
  };

  const handleInputKeyDown = async (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      await handleSend();
    }
  };

  const handleNewSession = async () => {
    if (createSessionMutation.isPending) {
      return;
    }
    await createSessionMutation.mutateAsync();
  };

  const handleDeleteSession = async (targetSessionId: string) => {
    if (deleteSessionMutation.isPending) {
      return;
    }
    const targetSession = sessions.find((session) => session.session_id === targetSessionId);
    const confirmed = window.confirm(`Delete session \"${targetSession?.title ?? 'AI Lab chat session'}\"?`);
    if (!confirmed) {
      return;
    }
    try {
      await deleteSessionMutation.mutateAsync(targetSessionId);
    } catch {
      // The session list is updated optimistically; stale or already-deleted sessions should not block cleanup.
    }
  };

  const toggleDocumentSelection = (documentId: string) => {
    setDraftDocumentIds((current) => {
      if (current.includes(documentId)) {
        return current.filter((item) => item !== documentId);
      }
      return [...current, documentId];
    });
  };

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto h-[calc(100vh-3.5rem)] min-h-[calc(100vh-3.5rem)] flex flex-col overflow-y-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="lab-document-experiments-header">
        <AiLabSectionIntro
          title="Document / Chat Experiments"
        description="Grounded document Q&A surface for probing the selected evidence, validating answers and persisting useful chat traces."
        operatorQuestion="Is RAG helping or just adding noise and cost?"
        badges={[
          { label: activeStatusLabel, variant: effectiveStatus === 'degraded' ? 'warning' : effectiveStatus === 'trace_only' ? 'default' : 'success' },
        ]}
        dataSource={data?.meta?.source}
        />
      </div>

      {(isError || sendMutation.isError) && (
        <GlassCard className="mb-4 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            {sendMutation.error instanceof Error
              ? sendMutation.error.message
              : error instanceof Error
                ? error.message
                : 'AI LAB chat is unavailable right now.'}
          </div>
        </GlassCard>
      )}

      <div className="flex-1 flex gap-4 min-h-0 pb-4" data-tour="lab-document-experiments-workspace">
        <div className="flex-1 flex flex-col min-w-0 min-h-0" data-tour="lab-document-experiments-main-panel">
          <div className="flex-1 min-h-[30rem] lg:min-h-[36rem] overflow-y-auto space-y-4 mb-4 pr-2" data-tour="lab-document-experiments-chat">
            {isLoading && !messages.length ? (
              <div className="glass rounded-xl p-4 text-xs text-muted-foreground">Loading AI LAB chat session…</div>
            ) : messages.length === 0 ? (
              <div className="glass rounded-xl p-4 text-xs text-muted-foreground">
                No chat session was recorded yet. Send the first grounded message to create a persisted AI LAB session.
              </div>
            ) : (
              messages.map((msg, index) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.06 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[80%] rounded-xl p-4 ${msg.role === 'user' ? 'bg-primary/10 border border-primary/20' : 'glass'}`}>
                    <div className="text-xs text-foreground leading-relaxed">{renderMessageContent(msg.content)}</div>
                    {msg.sources?.length ? (
                      <div className="mt-3 pt-3 border-t border-border/30">
                        <p className="text-[9px] text-muted-foreground/50 uppercase tracking-wider mb-1.5">Grounding</p>
                        <div className="flex items-center gap-2 flex-wrap">
                          {msg.sources.map((source, sourceIndex) => (
                            <span
                              key={`${msg.id}-${source.label}-${sourceIndex}`}
                              className="text-[10px] px-2 py-1 rounded-md bg-secondary/50 text-muted-foreground flex items-center gap-1"
                            >
                              <FileText className="w-3 h-3" />
                              {source.label}
                              {source.detail ? <span className="text-muted-foreground/70">· {source.detail}</span> : null}
                              {operatorPreferences.showSourceBadges ? (
                                typeof source.score === 'number' ? (
                                  <span className="text-primary/60">Retrieved</span>
                                ) : (
                                  <span className="text-muted-foreground/50">Grounded source</span>
                                )
                              ) : null}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </motion.div>
              ))
            )}
            {sendMutation.isPending ? (
              <div className="flex justify-start">
                <div className="glass rounded-xl p-4 flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Running live retrieval and generation…
                </div>
              </div>
            ) : null}
          </div>

          <div className="flex items-center gap-2 mb-3 flex-wrap">
            {(Array.isArray(data?.suggested_prompts) ? data.suggested_prompts : []).map((prompt) => (
              <button
                key={prompt}
                onClick={() => {
                  void handleSend(prompt);
                }}
                disabled={!canSend || sendMutation.isPending}
                className="text-[10px] px-3 py-1.5 rounded-lg bg-secondary/30 border border-border/50 text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Sparkles className="w-3 h-3 inline mr-1" />
                {prompt}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 glass rounded-xl p-2" data-tour="lab-document-experiments-prompt">
            <Input
              value={input}
              onChange={(event) => setInput(event.target.value.slice(0, CHAT_INPUT_MAX_CHARS))}
              onKeyDown={handleInputKeyDown}
              placeholder={canSend ? 'Ask about your documents…' : 'Select documents to ground this chat'}
              maxLength={CHAT_INPUT_MAX_CHARS}
              className="border-0 bg-transparent text-xs focus-visible:ring-0 h-8"
              disabled={!canSend || sendMutation.isPending}
            />
            <span className="px-2 text-[10px] text-muted-foreground tabular-nums">{input.length}/{CHAT_INPUT_MAX_CHARS}</span>
            <Button
              size="sm"
              className="bg-primary text-primary-foreground hover:bg-primary/90 h-8 w-8 p-0 shrink-0"
              aria-label="Send chat message"
              title="Send chat message"
              disabled={!canSend || sendMutation.isPending || !input.trim()}
              onClick={() => {
                void handleSend();
              }}
            >
              {sendMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            </Button>
          </div>
          {sendDisabledReason ? (
            <p className="mt-2 text-[10px] text-muted-foreground">{sendDisabledReason}</p>
          ) : null}
        </div>

        <div className="hidden lg:block w-72 space-y-4">
          <GlassCard data-tour="lab-document-experiments-sessions">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Sessions</h4>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    void handleNewSession();
                  }}
                  className="text-[10px] px-2 py-1 rounded-md border border-border/50 bg-secondary/20 text-muted-foreground hover:text-foreground hover:bg-secondary/30 transition-colors"
                >
                  New
                </button>
                {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
              </div>
            </div>
            <div className="space-y-2 max-h-[18rem] overflow-y-auto pr-1">
              {sessions.length === 0 ? (
                <p className="text-xs text-muted-foreground">No persisted sessions yet.</p>
              ) : (
                sessions.map((session) => (
                  <div
                    key={session.session_id}
                    className={`rounded-lg border px-3 py-2 transition-colors ${session.session_id === activeSessionId ? 'border-primary/30 bg-primary/10' : 'border-border/40 bg-secondary/20 hover:bg-secondary/30'}`}
                  >
                    <div className="flex items-start gap-2">
                      <button
                        onClick={() => setSessionId(session.session_id)}
                        className="flex-1 min-w-0 text-left"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs text-foreground truncate">{session.title}</span>
                          <FolderClock className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                        </div>
                        <div className="mt-1 text-[10px] text-muted-foreground flex items-center justify-between gap-2">
                          <span>{session.message_count} msg · {session.document_count ?? 0} docs</span>
                          <span>{session.updated_at ? new Date(session.updated_at).toLocaleString() : '—'}</span>
                        </div>
                        <div className="mt-1 text-[10px] text-muted-foreground flex items-center justify-between gap-2">
                          <span>{session.last_model ?? 'model n/a'}</span>
                          <span>{session.status ?? 'active'}</span>
                        </div>
                        {showActiveSessionError && session.session_id === activeSession?.session_id ? <p className="mt-1 text-[10px] text-glow-warning truncate">{activeSessionError}</p> : null}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          void handleDeleteSession(session.session_id);
                        }}
                        className="mt-0.5 rounded-md border border-border/40 bg-background/20 p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary/30 transition-colors disabled:opacity-50"
                        title="Delete session"
                        aria-label={`Delete ${session.title}`}
                        disabled={deleteSessionMutation.isPending}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard data-tour="lab-document-experiments-documents">
            <div className="flex items-center justify-between mb-3 gap-2">
              <div>
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Selected Documents</h4>
                <p className="mt-1 text-[10px] text-muted-foreground">{selectedDocuments.length} selected · applies to the next grounded turn</p>
              </div>
              <button
                type="button"
                onClick={() => setDocumentPickerOpen((current) => !current)}
                className="text-[10px] px-2 py-1 rounded-md border border-border/50 bg-secondary/20 text-muted-foreground hover:text-foreground hover:bg-secondary/30 transition-colors inline-flex items-center gap-1"
              >
                Choose
                {documentPickerOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>
            {documentPickerOpen ? (
              <div className="mb-3 rounded-lg border border-border/40 bg-secondary/10 p-2 space-y-2">
                <Input
                  value={documentFilter}
                  onChange={(event) => setDocumentFilter(event.target.value)}
                  placeholder="Filter documents..."
                  className="h-8 text-xs bg-background/40"
                />
                <div className="flex items-center justify-between px-1 text-[10px] text-muted-foreground">
                  <span>Indexed documents</span>
                  <span>{filteredAvailableDocuments.length} option{filteredAvailableDocuments.length === 1 ? '' : 's'}</span>
                </div>
                <div className="max-h-60 overflow-y-auto space-y-1 pr-1">
                  {filteredAvailableDocuments.length === 0 ? (
                    <p className="text-[10px] text-muted-foreground px-1 py-2">No documents match the current filter.</p>
                  ) : (
                    filteredAvailableDocuments.map((document) => {
                      const checked = selectedDocumentIds.includes(document.document_id);
                      return (
                        <label
                          key={document.document_id}
                          className="flex items-start gap-2 rounded-md border border-border/30 bg-background/20 px-2 py-1.5 text-xs text-muted-foreground hover:bg-secondary/20 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            className="mt-0.5 h-4 w-4 rounded border-border/60 bg-transparent"
                            checked={checked}
                            onChange={() => toggleDocumentSelection(document.document_id)}
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-foreground">{document.name}</span>
                            <span className="mt-0.5 block text-[10px] text-muted-foreground">
                              {document.status}
                              {typeof document.chunk_count === 'number' ? ` · ${document.chunk_count} chunk(s)` : ''}
                              {document.size_label ? ` · ${document.size_label}` : ''}
                            </span>
                          </span>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            ) : null}
            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {selectedDocuments.length === 0 ? (
                <p className="text-xs text-muted-foreground">No documents selected for the next grounded turn.</p>
              ) : (
                selectedDocuments.map((document) => (
                  <div key={document.document_id} className="py-1.5 border-b last:border-0 border-border/20">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <FileText className="w-3 h-3 shrink-0" />
                      <span className="truncate">{document.name}</span>
                    </div>
                    <div className="ml-5 mt-1 text-[10px] text-muted-foreground flex items-center gap-2 flex-wrap">
                      <span>{document.status}</span>
                      {typeof document.chunk_count === 'number' ? <span>{document.chunk_count} chunk(s)</span> : null}
                      {document.size_label ? <span>{document.size_label}</span> : null}
                      {document.loader_strategy_label ? <span>{document.loader_strategy_label}</span> : null}
                    </div>
                    {document.warnings?.length ? <p className="ml-5 mt-1 text-[10px] text-glow-warning">{document.warnings.join(' · ')}</p> : null}
                  </div>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard data-tour="lab-document-experiments-activity">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Recent activity</h4>
              {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-2 max-h-[18rem] overflow-y-auto pr-1">
              {sessionTimeline.length === 0 ? (
                <p className="text-xs text-muted-foreground">No persisted timeline yet.</p>
              ) : (
                sessionTimeline.map((event) => (
                  <div key={event.id} className="rounded-lg border border-border/30 bg-secondary/20 p-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] text-foreground font-medium">{event.label}</span>
                      <span className="text-[10px] text-muted-foreground">{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '—'}</span>
                    </div>
                    <p className="mt-1 text-[10px] text-muted-foreground">{event.detail ?? 'Recorded event'}</p>
                  </div>
                ))
              )}
            </div>
          </GlassCard>
        </div>
      </div>
    </motion.div>
  );
}

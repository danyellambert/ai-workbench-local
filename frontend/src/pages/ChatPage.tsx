import { motion } from 'framer-motion';
import { KeyboardEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, Send, FileText, Sparkles, Activity, Database, Clock, Gauge, AlertTriangle, Loader2, FolderClock } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { GlassCard } from '@/components/shared/ui-components';
import { aiLabQueryKeys, createLabChatSession, getLabChatPage, sendLabChatMessage } from '@/lib/ai-lab-data';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAppStore } from '@/lib/store';

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

function normalizeMessageSources(sources: unknown) {
  if (!Array.isArray(sources)) {
    return [];
  }

  return sources.flatMap((source, index) => {
    if (!source || typeof source !== 'object') {
      return [];
    }

    const record = source as Record<string, unknown>;
    const rawScore = typeof record.score === 'number' ? record.score : null;
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
      },
    ];
  });
}

function normalizeMessages(messages: unknown) {
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

function normalizeSessions(sessions: unknown) {
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
      },
    ];
  });
}

function normalizeDocuments(documents: unknown) {
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
        ...record,
        document_id: documentId,
        name:
          typeof record.name === 'string'
            ? record.name
            : typeof record.title === 'string'
              ? record.title
              : `Document ${index + 1}`,
      },
    ];
  });
}

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const operatorPreferences = useAppStore((state) => state.operatorPreferences);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: aiLabQueryKeys.chat(sessionId),
    queryFn: () => getLabChatPage(sessionId),
    retry: false,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (data?.active_session_id && data.active_session_id !== sessionId) {
      setSessionId(data.active_session_id);
    }
  }, [data?.active_session_id, sessionId]);

  const selectedDocuments = useMemo(() => normalizeDocuments(data?.selected_documents), [data?.selected_documents]);
  const selectedDocumentIds = useMemo(
    () => selectedDocuments.map((document) => document.document_id).filter(Boolean),
    [selectedDocuments],
  );
  const messages = useMemo(() => normalizeMessages(data?.messages), [data?.messages]);
  const sessions = useMemo(() => normalizeSessions(data?.sessions), [data?.sessions]);
  const sessionDiagnostics = useMemo(() => normalizeRows(data?.session_diagnostics), [data?.session_diagnostics]);
  const retrievalQuality = useMemo(() => normalizeRows(data?.retrieval_quality), [data?.retrieval_quality]);
  const metaNotes = useMemo(
    () => (Array.isArray(data?.meta?.notes) ? data.meta.notes.filter((note): note is string => typeof note === 'string') : []),
    [data?.meta?.notes],
  );

  const sendMutation = useMutation({
    mutationFn: async () => {
      const content = input.trim();
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

  const canSend = Boolean(data?.capabilities?.can_send);
  const retrievalStrategy = retrievalQuality.find((row) => row.label === 'Strategy')?.value ?? 'trace_only';
  const topK = sessionDiagnostics.find((row) => row.label === 'Top-K')?.value ?? '—';
  const activeSessionId = data?.active_session_id ?? sessionId ?? sessions[0]?.session_id ?? null;
  const activeSession = sessions.find((item) => item.session_id === activeSessionId) ?? sessions[0];

  const handleSend = async () => {
    if (!canSend || sendMutation.isPending || !input.trim()) {
      return;
    }
    await sendMutation.mutateAsync();
  };

  const handleInputKeyDown = async (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      await handleSend();
    }
  };

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto h-[calc(100vh-3.5rem)] flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Document / Chat Experiments"
        description="Diagnostic RAG surface for document interaction, retrieval quality assessment and grounding validation."
        operatorQuestion="Is RAG helping or just adding noise and cost?"
        badges={[
          { label: canSend ? 'Live session' : 'Degraded', variant: canSend ? 'success' : 'warning' },
          { label: String(retrievalStrategy), variant: 'default' },
          { label: `top-k: ${topK}`, variant: 'default' },
        ]}
        dataSource={data?.meta?.source}
      />

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

      <div className="flex-1 flex gap-4 min-h-0">
        <div className="flex-1 flex flex-col min-w-0">
          {metaNotes.length ? (
            <div className="mb-4 rounded-xl border border-border/50 bg-secondary/20 px-4 py-3 text-[11px] text-muted-foreground">
              {metaNotes.join(' ')}
            </div>
          ) : null}

          <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
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
                    <p className="text-xs text-foreground leading-relaxed whitespace-pre-line">{msg.content}</p>
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
                              {operatorPreferences.showSourceBadges && typeof source.score === 'number' ? (
                                <span className="text-primary/60">{source.score.toFixed(0)}%</span>
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
                onClick={() => setInput(prompt)}
                className="text-[10px] px-3 py-1.5 rounded-lg bg-secondary/30 border border-border/50 text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
              >
                <Sparkles className="w-3 h-3 inline mr-1" />
                {prompt}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 glass rounded-xl p-2">
            <Input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder={canSend ? 'Ask about your documents…' : 'AI LAB chat is unavailable in the current runtime'}
              className="border-0 bg-transparent text-xs focus-visible:ring-0 h-8"
              disabled={!canSend || sendMutation.isPending}
            />
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
          {!canSend && data?.capabilities?.reason ? (
            <p className="mt-2 text-[10px] text-muted-foreground">{data.capabilities.reason}</p>
          ) : null}
        </div>

        <div className="hidden lg:block w-72 space-y-4">
          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Sessions</h4>
              {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-2">
              {sessions.length === 0 ? (
                <p className="text-xs text-muted-foreground">No persisted sessions yet.</p>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => setSessionId(session.session_id)}
                    className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${session.session_id === activeSessionId ? 'border-primary/30 bg-primary/10' : 'border-border/40 bg-secondary/20 hover:bg-secondary/30'}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-foreground truncate">{session.title}</span>
                      <FolderClock className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    </div>
                    <div className="mt-1 text-[10px] text-muted-foreground flex items-center justify-between gap-2">
                      <span>{session.message_count} msg</span>
                      <span>{session.updated_at ? new Date(session.updated_at).toLocaleString() : '—'}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Selected Documents</h4>
              {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-2">
              {selectedDocuments.length === 0 ? (
                <p className="text-xs text-muted-foreground">No indexed documents are currently visible to the chat runtime.</p>
              ) : (
                selectedDocuments.map((document) => (
                  <div key={document.document_id} className="flex items-center gap-2 text-xs text-muted-foreground py-1">
                    <FileText className="w-3 h-3 shrink-0" />
                    <span className="truncate">{document.name}</span>
                  </div>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Session Diagnostics</h4>
              {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-2 text-[10px] text-muted-foreground">
              {sessionDiagnostics.map((row) => {
                const Icon = row.label === 'Messages'
                  ? MessageSquare
                  : row.label.includes('Token')
                    ? Database
                    : row.label.toLowerCase().includes('latency')
                      ? Clock
                      : row.label.includes('Top-K') || row.label.includes('Context')
                        ? Gauge
                        : Activity;
                return (
                  <div key={row.label} className="flex justify-between items-center gap-4">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <Icon className="w-3 h-3 shrink-0" />
                      <span className="truncate">{row.label}</span>
                    </div>
                    <span className="text-foreground font-mono text-right">{row.value}</span>
                  </div>
                );
              })}
            </div>
          </GlassCard>

          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Retrieval Quality</h4>
              {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-2 text-[10px] text-muted-foreground">
              {retrievalQuality.map((row) => (
                <div key={row.label} className="flex justify-between gap-4">
                  <span>{row.label}</span>
                  <span className="text-foreground font-mono text-right">{row.value}</span>
                </div>
              ))}
            </div>
            {activeSession?.updated_at ? (
              <p className="mt-3 text-[10px] text-muted-foreground">Last updated {new Date(activeSession.updated_at).toLocaleString()}</p>
            ) : null}
          </GlassCard>
        </div>
      </div>
    </motion.div>
  );
}

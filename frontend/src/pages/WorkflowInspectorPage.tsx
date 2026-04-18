import { motion } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Workflow, Play, GitBranch, ShieldAlert, Eye, Clock, Zap, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabWorkflowInspectorPage, runLabWorkflowInspector } from '@/lib/ai-lab-data';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore } from '@/lib/store';

function toStatus(status: string): string {
  if (status === 'completed' || status === 'success') return 'completed';
  if (status === 'warning') return 'warning';
  return 'error';
}

export default function WorkflowInspectorPage() {
  const autoOpenInspectorDetails = useAppStore((state) => state.operatorPreferences.autoOpenInspectorDetails);
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: aiLabQueryKeys.workflowInspector(),
    queryFn: () => getLabWorkflowInspectorPage(),
    retry: false,
    refetchOnWindowFocus: false,
  });

  const [selectedTask, setSelectedTask] = useState<string>('');
  const [selectedDocument, setSelectedDocument] = useState<string>('');
  const [instructions, setInstructions] = useState('');

  useEffect(() => {
    if (!selectedTask && data?.selected_task_id) {
      setSelectedTask(data.selected_task_id);
    }
  }, [data?.selected_task_id, selectedTask]);

  useEffect(() => {
    if (!selectedDocument && data?.document_options?.length) {
      setSelectedDocument(data.document_options[0].id);
    }
  }, [data?.document_options, selectedDocument]);

  const currentTask = useMemo(() => {
    const fallbackTask = data?.selected_task_id ?? data?.task_options[0]?.id ?? '';
    return selectedTask || fallbackTask;
  }, [data?.selected_task_id, data?.task_options, selectedTask]);

  const taskOptions = data?.task_options ?? [];
  const documentOptions = data?.document_options ?? [];
  const recentCases = data?.recent_cases ?? [];
  const selectedDetail = currentTask ? data?.task_details[currentTask] : undefined;
  const summary = data?.summary;
  const canExecute = Boolean(data?.capabilities.can_execute);
  const modeCounts = recentCases.reduce<Record<string, number>>((acc, item) => {
    acc[item.mode] = (acc[item.mode] || 0) + 1;
    return acc;
  }, {});

  useEffect(() => {
    if (!instructions && selectedDetail?.document_names?.length) {
      setInstructions(`Review ${selectedDetail.document_names.slice(0, 2).join(', ')} and summarize the main findings, risks and next actions.`);
    }
  }, [instructions, selectedDetail?.document_names]);

  const runMutation = useMutation({
    mutationFn: async () => runLabWorkflowInspector({
      task_id: currentTask,
      document_id: selectedDocument || null,
      input_text: instructions.trim() || undefined,
    }),
    onSuccess: (response) => {
      queryClient.setQueryData(aiLabQueryKeys.workflowInspector(), response.page);
      queryClient.invalidateQueries({ queryKey: ['ai-lab', 'workflow-inspector'] });
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.artifacts });
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.runtime });
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.overview });
      queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.evidenceOps });
      const nextTask = typeof response.run?.task_id === 'string' ? response.run.task_id : currentTask;
      setSelectedTask(nextTask);
    },
  });

  const handleRun = async () => {
    if (!canExecute || runMutation.isPending || !currentTask) {
      return;
    }
    await runMutation.mutateAsync();
  };

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Workflow Inspector"
        description="Structured execution engine with routing decisions, guardrail triggers and auditability."
        operatorQuestion="Why did the workflow choose this route, and what triggered review?"
        badges={[
          { label: `${summary?.total_cases ?? 0} recent traces`, variant: 'default' },
          {
            label: `${summary?.needs_review ?? 0} needs review`,
            variant: (summary?.needs_review ?? 0) > 0 ? 'warning' : 'success',
          },
          {
            label: canExecute ? 'Live execution' : 'Degraded',
            variant: canExecute ? 'success' : 'warning',
          },
        ]}
        dataSource={data?.meta.source}
      />

      {(isError || runMutation.isError) && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            {runMutation.error instanceof Error
              ? runMutation.error.message
              : error instanceof Error
                ? error.message
                : 'Workflow Inspector is unavailable right now.'}
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={5}
        metrics={[
          { label: 'Total Cases', value: summary?.total_cases ?? '—', icon: Workflow, status: 'neutral' },
          { label: 'Needs Review', value: summary?.needs_review ?? '—', icon: Eye, status: (summary?.needs_review ?? 0) > 2 ? 'warning' : 'healthy' },
          { label: 'Avg Confidence', value: summary ? `${summary.avg_confidence}%` : '—', icon: Zap, status: 'healthy' },
          { label: 'Review Blockers', value: summary?.review_blockers ?? '—', icon: ShieldAlert, status: (summary?.review_blockers ?? 0) > 0 ? 'warning' : 'healthy' },
          { label: 'Failed', value: summary?.failed ?? '—', icon: AlertTriangle, status: (summary?.failed ?? 0) > 0 ? 'error' : 'healthy' },
        ]}
      />

      <div className="grid lg:grid-cols-12 gap-4 mb-6">
        <div className="lg:col-span-4 space-y-4">
          <GlassCard delay={0.1}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Task Selection</h4>
            <div className="space-y-1.5">
              {taskOptions.map((task) => (
                <button
                  key={task.id}
                  onClick={() => {
                    setSelectedTask(task.id);
                    if (!instructions.trim()) {
                      setInstructions(`Run ${task.label.toLowerCase()} on the selected evidence and summarize the operational outcome.`);
                    }
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                    currentTask === task.id
                      ? 'bg-primary/10 text-primary border border-primary/20'
                      : 'hover:bg-secondary/30 text-muted-foreground'
                  }`}
                >
                  <div className="min-w-0">
                    <p className="text-xs font-medium">{task.label}</p>
                    <p className="text-[10px] text-muted-foreground/70 truncate">{task.description}</p>
                    <p className="text-[9px] text-muted-foreground/50 mt-1">{task.recent_count} persisted trace(s)</p>
                  </div>
                </button>
              ))}
              {isLoading && taskOptions.length === 0 && <p className="text-xs text-muted-foreground">Loading task traces…</p>}
            </div>
          </GlassCard>

          <GlassCard delay={0.15}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Document</h4>
            <Select value={selectedDocument} onValueChange={setSelectedDocument} disabled={documentOptions.length === 0 || runMutation.isPending}>
              <SelectTrigger className="h-8 text-xs bg-secondary/30 border-border/50"><SelectValue placeholder="Select a document" /></SelectTrigger>
              <SelectContent>
                {documentOptions.map((document) => (
                  <SelectItem key={document.id} value={document.id} className="text-xs">
                    {document.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="mt-2 text-[10px] text-muted-foreground">
              This selector now feeds real AI LAB workflow execution and persists the resulting trace for later inspection.
            </p>
          </GlassCard>

          <GlassCard delay={0.2}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Instructions</h4>
            <Textarea
              placeholder={canExecute ? 'Describe the run you want to execute…' : 'Workflow execution is unavailable in the current runtime…'}
              className="text-xs bg-secondary/30 border-border/50 min-h-[84px]"
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              disabled={!canExecute || runMutation.isPending}
            />
          </GlassCard>

          <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90 h-9 text-xs" disabled={!canExecute || runMutation.isPending || !currentTask} onClick={() => void handleRun()}>
            {runMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-2" />}
            {runMutation.isPending ? 'Executing…' : canExecute ? 'Execute Task' : 'Execution unavailable'}
          </Button>
          {data?.capabilities.reason ? <p className="text-[10px] text-muted-foreground">{data.capabilities.reason}</p> : null}
        </div>

        <div className="lg:col-span-8">
          <Tabs defaultValue={autoOpenInspectorDetails ? 'metadata' : 'visual'}>
            <TabsList className="bg-secondary/30 border border-border/50 mb-4">
              <TabsTrigger value="visual" className="text-xs data-[state=active]:bg-secondary">Result</TabsTrigger>
              <TabsTrigger value="json" className="text-xs data-[state=active]:bg-secondary">JSON</TabsTrigger>
              <TabsTrigger value="routing" className="text-xs data-[state=active]:bg-secondary">Routing</TabsTrigger>
              <TabsTrigger value="metadata" className="text-xs data-[state=active]:bg-secondary">Metadata</TabsTrigger>
            </TabsList>

            <TabsContent value="visual" className="mt-0">
              <GlassCard>
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                  <CheckCircle2 className="w-4 h-4 text-glow-success" />
                  <h3 className="text-sm font-medium text-foreground">{selectedDetail?.result_title ?? 'Latest persisted trace'}</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border/50">
                    {selectedDetail?.result_items.length ?? 0} item(s)
                  </span>
                  {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
                </div>

                {selectedDetail?.document_names?.length ? (
                  <div className="flex items-center gap-2 flex-wrap mb-4">
                    {selectedDetail.document_names.map((name) => (
                      <span key={name} className="text-[10px] px-2 py-1 rounded bg-secondary/30 text-muted-foreground border border-border/40">
                        {name}
                      </span>
                    ))}
                  </div>
                ) : null}

                {selectedDetail?.result_items?.length ? (
                  <div className="space-y-2">
                    {selectedDetail.result_items.map((item, index) => (
                      <motion.div
                        key={`${item.label}-${index}`}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 + index * 0.04 }}
                        className="flex items-center justify-between py-2.5 px-3 rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors gap-4"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary font-medium shrink-0">{item.label}</span>
                          <span className="text-xs text-foreground truncate">{item.value}</span>
                        </div>
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {typeof item.confidence === 'number' ? `${Math.round(item.confidence * 100)}%` : '—'}
                        </span>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-border/40 bg-secondary/20 p-4 text-xs text-muted-foreground">
                    No structured result payload was persisted for this trace yet.
                  </div>
                )}
              </GlassCard>
            </TabsContent>

            <TabsContent value="json" className="mt-0">
              <GlassCard>
                <pre className="text-xs text-foreground/80 font-mono leading-relaxed overflow-auto max-h-[500px]">
                  {JSON.stringify(selectedDetail?.raw_json ?? {}, null, 2)}
                </pre>
              </GlassCard>
            </TabsContent>

            <TabsContent value="routing" className="mt-0 space-y-3">
              {(selectedDetail?.executions ?? []).length === 0 ? (
                <GlassCard>
                  <p className="text-xs text-muted-foreground">No execution trail is available for the selected task yet.</p>
                </GlassCard>
              ) : (
                (selectedDetail?.executions ?? []).map((execution, index) => (
                  <GlassCard key={execution.id} delay={0.05 + index * 0.04}>
                    <div className="flex items-center justify-between mb-3 gap-4">
                      <div className="flex items-center gap-2 flex-wrap">
                        <GitBranch className="w-4 h-4 text-primary" />
                        <span className="text-xs font-medium text-foreground capitalize">{execution.mode.replace(/_/g, ' ')}</span>
                        <StatusPill status={toStatus(execution.status)} />
                        {execution.needs_review && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-glow-warning/10 text-glow-warning border border-glow-warning/20">Needs Review</span>
                        )}
                      </div>
                      <span className="text-[10px] text-muted-foreground text-right">
                        {typeof execution.latency_s === 'number' ? `${execution.latency_s.toFixed(1)}s` : '—'} · {execution.source_count} source(s)
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-[10px] mb-2">
                      <div>
                        <span className="text-muted-foreground block">Confidence</span>
                        <span className="text-foreground font-medium">{Math.round((execution.confidence || 0) * 100)}%</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block">Model</span>
                        <span className="text-foreground font-medium">{execution.model ?? '—'}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block">Provider</span>
                        <span className="text-foreground font-medium">{execution.provider ?? '—'}</span>
                      </div>
                    </div>
                    {execution.review_reason ? (
                      <div className="text-[10px] text-muted-foreground bg-secondary/20 rounded p-2 mt-2">
                        <ShieldAlert className="w-3 h-3 inline mr-1 text-glow-warning" />
                        {execution.review_reason}
                      </div>
                    ) : null}
                  </GlassCard>
                ))
              )}
            </TabsContent>

            <TabsContent value="metadata" className="mt-0">
              <GlassCard>
                <h3 className="text-sm font-medium text-foreground mb-3">Execution Metadata</h3>
                <div className="space-y-2 text-xs">
                  {(selectedDetail?.trace_fields ?? []).map((field) => (
                    <div key={field.label} className="flex justify-between py-1.5 border-b border-border/20 last:border-0 gap-4">
                      <span className="text-muted-foreground">{field.label}</span>
                      <span className="text-foreground font-mono text-[11px] text-right">{field.value}</span>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <GlassCard delay={0.3}>
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <Clock className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Recent Cases</h3>
          {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          <span className="text-[10px] text-muted-foreground">observed modes: {Object.entries(modeCounts).map(([mode, count]) => `${mode} ${count}`).join(' · ') || '—'}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50">
                {['Task', 'Document', 'Mode', 'Status', 'Confidence', 'Sources', 'Review'].map((heading) => (
                  <th key={heading} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recentCases.map((item) => (
                <tr key={item.id} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                  <td className="px-3 py-2.5 text-xs text-foreground">{item.task}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground truncate max-w-[220px]">{item.document}</td>
                  <td className="px-3 py-2.5">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-secondary text-foreground font-mono">{item.mode}</span>
                  </td>
                  <td className="px-3 py-2.5"><StatusPill status={toStatus(item.status)} /></td>
                  <td className="px-3 py-2.5 text-xs text-foreground">{item.confidence > 0 ? `${Math.round(item.confidence * 100)}%` : '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-foreground">{item.sourceCount}</td>
                  <td className="px-3 py-2.5">
                    {item.needsReview ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-glow-warning/10 text-glow-warning border border-glow-warning/20">Yes</span>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">No</span>
                    )}
                  </td>
                </tr>
              ))}
              {isLoading && recentCases.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-xs text-muted-foreground">Loading recent cases…</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </motion.div>
  );
}

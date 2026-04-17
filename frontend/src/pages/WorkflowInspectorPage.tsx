import { motion } from 'framer-motion';
import { useState } from 'react';
import { Workflow, Play, FileText, GitBranch, ShieldAlert, Eye, Clock, Zap, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { getWorkflowCases, getWorkflowAttempts } from '@/lib/ai-lab-data';
import { structuredTasks, documents } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore } from '@/lib/store';

const cases = getWorkflowCases();
const attempts = getWorkflowAttempts();

const reviewCases = cases.data.filter(c => c.needsReview);
const routeCounts = cases.data.reduce<Record<string, number>>((acc, c) => { acc[c.route] = (acc[c.route] || 0) + 1; return acc; }, {});

export default function WorkflowInspectorPage() {
  const [selectedTask, setSelectedTask] = useState('extraction');
  const autoOpenInspectorDetails = useAppStore((state) => state.operatorPreferences.autoOpenInspectorDetails);

  const sampleOutput = {
    task: 'extraction', document: 'Master Service Agreement v4.2',
    model: 'qwen2.5:32b-instruct',
    entities: [
      { type: 'Contracting Party', value: 'Meridian Holdings Ltd.', confidence: 0.96 },
      { type: 'Effective Date', value: '2024-01-15', confidence: 0.99 },
      { type: 'Annual Value', value: '$2,400,000', confidence: 0.94 },
      { type: 'Term Duration', value: '36 months', confidence: 0.97 },
      { type: 'Governing Law', value: 'State of Delaware', confidence: 0.92 },
      { type: 'Liability Cap', value: 'Unlimited (Section 7.3)', confidence: 0.94 },
      { type: 'Notice Period', value: '90 days (auto-renewal)', confidence: 0.91 },
    ],
  };

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Workflow Inspector"
        description="Structured execution engine with routing decisions, guardrail triggers and auditability."
        operatorQuestion="Why did the workflow choose this route, and what triggered review?"
        badges={[
          { label: `${cases.data.length} recent cases` },
          { label: `${reviewCases.length} needs review`, variant: reviewCases.length > 0 ? 'warning' : 'success' },
          { label: `Direct: ${routeCounts['direct'] || 0} / LangGraph: ${routeCounts['langgraph'] || 0}` },
        ]}
        dataSource={cases.meta.source}
      />

      <AiLabMetricGrid columns={5} metrics={[
        { label: 'Total Cases', value: cases.data.length, icon: Workflow, status: 'neutral' },
        { label: 'Needs Review', value: reviewCases.length, icon: Eye, status: reviewCases.length > 2 ? 'warning' : 'healthy' },
        { label: 'Avg Confidence', value: `${Math.round(cases.data.reduce((s, c) => s + c.confidence, 0) / cases.data.length * 100)}%`, icon: Zap, status: 'healthy' },
        { label: 'Guardrails Triggered', value: attempts.data.filter(a => a.guardrailTriggered).length, icon: ShieldAlert, status: 'warning' },
        { label: 'Failed', value: cases.data.filter(c => c.status === 'failed').length, icon: AlertTriangle, status: cases.data.some(c => c.status === 'failed') ? 'error' : 'healthy' },
      ]} />

      <div className="grid lg:grid-cols-12 gap-4 mb-6">
        {/* Controls */}
        <div className="lg:col-span-4 space-y-4">
          <GlassCard delay={0.1}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Task Selection</h4>
            <div className="space-y-1.5">
              {structuredTasks.map(task => (
                <button key={task.id} onClick={() => setSelectedTask(task.name)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                    selectedTask === task.name ? 'bg-primary/10 text-primary border border-primary/20' : 'hover:bg-secondary/30 text-muted-foreground'
                  }`}>
                  <div className="min-w-0">
                    <p className="text-xs font-medium">{task.label}</p>
                    <p className="text-[10px] text-muted-foreground/70 truncate">{task.description}</p>
                  </div>
                </button>
              ))}
            </div>
          </GlassCard>

          <GlassCard delay={0.15}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Document</h4>
            <Select defaultValue="d1">
              <SelectTrigger className="h-8 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
              <SelectContent>{documents.filter(d => d.status === 'indexed').map(d => (
                <SelectItem key={d.id} value={d.id} className="text-xs">{d.name}</SelectItem>
              ))}</SelectContent>
            </Select>
          </GlassCard>

          <GlassCard delay={0.2}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Instructions</h4>
            <Textarea placeholder="Optional additional instructions..." className="text-xs bg-secondary/30 border-border/50 min-h-[60px]" />
          </GlassCard>

          <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90 h-9 text-xs">
            <Play className="w-3.5 h-3.5 mr-2" /> Execute Task
          </Button>
        </div>

        {/* Results */}
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
                <div className="flex items-center gap-2 mb-4">
                  <CheckCircle2 className="w-4 h-4 text-glow-success" />
                  <h3 className="text-sm font-medium text-foreground">Extraction Results — Master Service Agreement v4.2</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-success/10 text-glow-success border border-glow-success/20">{sampleOutput.entities.length} entities</span>
                  <DataSourceBadge source="mock" />
                </div>
                <div className="space-y-2">
                  {sampleOutput.entities.map((e, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.2 + i * 0.04 }}
                      className="flex items-center justify-between py-2.5 px-3 rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors">
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary font-medium">{e.type}</span>
                        <span className="text-xs text-foreground">{e.value}</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground">{(e.confidence * 100).toFixed(0)}%</span>
                    </motion.div>
                  ))}
                </div>
              </GlassCard>
            </TabsContent>

            <TabsContent value="json" className="mt-0">
              <GlassCard>
                <pre className="text-xs text-foreground/80 font-mono leading-relaxed overflow-auto max-h-[500px]">
                  {JSON.stringify(sampleOutput, null, 2)}
                </pre>
              </GlassCard>
            </TabsContent>

            <TabsContent value="routing" className="mt-0 space-y-3">
              {attempts.data.map((a, i) => (
                <GlassCard key={a.id} delay={0.1 + i * 0.05}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <GitBranch className="w-4 h-4 text-primary" />
                      <span className="text-xs font-medium text-foreground capitalize">{a.route} route</span>
                      <StatusPill status={a.status === 'completed' ? 'completed' : 'error'} />
                      {a.needsReview && <span className="text-[10px] px-2 py-0.5 rounded bg-glow-warning/10 text-glow-warning border border-glow-warning/20">Needs Review</span>}
                    </div>
                    <span className="text-[10px] text-muted-foreground">{(a.durationMs / 1000).toFixed(1)}s · {a.tokenCount.toLocaleString()} tokens</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-[10px] mb-2">
                    <div><span className="text-muted-foreground block">Confidence</span><span className="text-foreground font-medium">{(a.confidence * 100).toFixed(0)}%</span></div>
                    <div><span className="text-muted-foreground block">Quality</span><span className="text-foreground font-medium">{(a.qualityScore * 100).toFixed(0)}%</span></div>
                    <div><span className="text-muted-foreground block">Guardrail</span><span className={a.guardrailTriggered ? 'text-glow-warning font-medium' : 'text-foreground'}>{a.guardrailTriggered ? 'Triggered' : 'Clear'}</span></div>
                  </div>
                  {a.guardrailReason && (
                    <div className="text-[10px] text-muted-foreground bg-secondary/20 rounded p-2 mt-2">
                      <ShieldAlert className="w-3 h-3 inline mr-1 text-glow-warning" />{a.guardrailReason}
                    </div>
                  )}
                </GlassCard>
              ))}
            </TabsContent>

            <TabsContent value="metadata" className="mt-0">
              <GlassCard>
                <h3 className="text-sm font-medium text-foreground mb-3">Execution Metadata</h3>
                <div className="space-y-2 text-xs">
                  {[['Task', 'extraction'], ['Document', 'Master Service Agreement v4.2'], ['Model', 'qwen2.5:32b-instruct'], ['Provider', 'ollama'],
                    ['Route Selected', 'direct'], ['Duration', '8.4s'], ['Tokens', '3,420'],
                    ['Confidence', '94%'], ['Quality Score', '91%'], ['Needs Review', 'No'],
                    ['Retrieval Strategy', 'hybrid_rerank'], ['Top-K', '15'],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between py-1.5 border-b border-border/20 last:border-0">
                      <span className="text-muted-foreground">{k}</span>
                      <span className="text-foreground font-mono text-[11px]">{v}</span>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Recent Cases */}
      <GlassCard delay={0.3}>
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Recent Cases</h3>
          <DataSourceBadge source="mock" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50">
                {['Task', 'Document', 'Route', 'Status', 'Confidence', 'Quality', 'Review'].map(h => (
                  <th key={h} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cases.data.map(c => (
                <tr key={c.id} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                  <td className="px-3 py-2.5 text-xs text-foreground">{c.task}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground truncate max-w-[200px]">{c.document}</td>
                  <td className="px-3 py-2.5"><span className="text-[10px] px-2 py-0.5 rounded bg-secondary text-foreground font-mono">{c.route}</span></td>
                  <td className="px-3 py-2.5"><StatusPill status={c.status === 'completed' ? 'completed' : 'error'} /></td>
                  <td className="px-3 py-2.5 text-xs text-foreground">{c.confidence > 0 ? `${(c.confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td className="px-3 py-2.5 text-xs text-foreground">{c.qualityScore > 0 ? `${(c.qualityScore * 100).toFixed(0)}%` : '—'}</td>
                  <td className="px-3 py-2.5">{c.needsReview && <span className="text-[10px] px-2 py-0.5 rounded bg-glow-warning/10 text-glow-warning border border-glow-warning/20">Yes</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </motion.div>
  );
}
import { motion } from 'framer-motion';
import { Terminal, Activity, Search, Wrench, RefreshCw, Radio, Shield, Clock, Users, AlertTriangle } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { mcpTools } from '@/lib/mock-data';
import { getOpenActions, getAutoOperations } from '@/lib/ai-lab-data';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const actions = getOpenActions();
const operations = getAutoOperations();

const telemetry = [
  { event: 'tool_call', tool: 'search_documents', latency: '340ms', status: 'ok', ts: '2024-03-15T10:30:00Z' },
  { event: 'tool_call', tool: 'list_open_actions', latency: '120ms', status: 'ok', ts: '2024-03-15T10:45:00Z' },
  { event: 'drift_check', tool: 'detect_repository_drift', latency: '2.4s', status: 'warning', ts: '2024-03-14T12:00:00Z' },
  { event: 'sync_plan', tool: 'register_external_sync', latency: '—', status: 'skipped', ts: '' },
  { event: 'auto_register', tool: 'auto_register', latency: '560ms', status: 'ok', ts: '2024-03-15T06:00:00Z' },
];

const readiness = [
  { target: 'Ingestion', status: 'partial', detail: '7/10 docs indexed, 1 error (Technical Architecture Brief), 1 indexing, 1 pending' },
  { target: 'Evals', status: 'partial', detail: '5 suites active, 2 failures (extraction_entities, candidate_scoring)' },
  { target: 'Benchmarks', status: 'ready', detail: '5 models benchmarked, production profile confirmed (Qwen 2.5)' },
  { target: 'MCP Tools', status: 'ready', detail: '4/6 tools active, 1 degraded (detect_repository_drift)' },
  { target: 'Governance', status: 'partial', detail: '4 open actions, 1 blocked (Phi-3 benchmark awaiting GPU allocation)' },
];

const priorityStyle: Record<string, string> = {
  high: 'bg-glow-error/10 text-glow-error border-glow-error/20',
  medium: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
  low: 'bg-muted text-muted-foreground border-border',
};

export default function EvidenceOpsPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="EvidenceOps / MCP"
        description="Operational governance console — MCP tool health, automated operations, action tracking and readiness."
        operatorQuestion="Is operations/governance healthy and controllable?"
        badges={[
          { label: `${mcpTools.filter(t => t.status === 'active').length}/${mcpTools.length} tools active`, variant: 'success' },
          { label: `${actions.data.filter(a => a.status !== 'done').length} open actions`, variant: 'warning' },
          { label: 'MCP v1.2.0', variant: 'default' },
        ]}
        dataSource="mock"
      >
        <Button variant="outline" className="h-9 px-4 text-xs border-border/50"><RefreshCw className="w-3.5 h-3.5 mr-2" /> Sync</Button>
      </AiLabSectionIntro>

      <AiLabMetricGrid columns={5} metrics={[
        { label: 'MCP Tools', value: mcpTools.length, icon: Wrench, status: 'neutral' },
        { label: 'Active', value: mcpTools.filter(t => t.status === 'active').length, icon: Activity, status: 'healthy' },
        { label: 'Open Actions', value: actions.data.filter(a => a.status !== 'done').length, icon: AlertTriangle, status: 'warning' },
        { label: 'Auto Ops (24h)', value: operations.data.length, icon: RefreshCw, status: 'neutral' },
        { label: 'Last Sync', value: '2h ago', icon: Clock, status: 'neutral' },
      ]} />

      <Tabs defaultValue="tools">
        <TabsList className="bg-secondary/30 border border-border/50 mb-4">
          <TabsTrigger value="tools" className="text-xs data-[state=active]:bg-secondary">MCP Tools</TabsTrigger>
          <TabsTrigger value="actions" className="text-xs data-[state=active]:bg-secondary">Open Actions</TabsTrigger>
          <TabsTrigger value="operations" className="text-xs data-[state=active]:bg-secondary">Auto Operations</TabsTrigger>
          <TabsTrigger value="telemetry" className="text-xs data-[state=active]:bg-secondary">Telemetry</TabsTrigger>
          <TabsTrigger value="readiness" className="text-xs data-[state=active]:bg-secondary">Readiness</TabsTrigger>
          <TabsTrigger value="search" className="text-xs data-[state=active]:bg-secondary">Search</TabsTrigger>
        </TabsList>

        <TabsContent value="tools" className="mt-0 space-y-3">
          {mcpTools.map((tool, i) => (
            <motion.div key={tool.name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.04 }}
              className="glass rounded-xl p-4 hover:border-primary/20 transition-all duration-300">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-secondary/50 flex items-center justify-center">
                    <Wrench className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div>
                    <h4 className="text-xs font-medium text-foreground font-mono">{tool.name}</h4>
                    <p className="text-[10px] text-muted-foreground">{tool.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusPill status={tool.status} />
                  {tool.lastCall && <span className="text-[10px] text-muted-foreground">{new Date(tool.lastCall).toLocaleTimeString()}</span>}
                </div>
              </div>
            </motion.div>
          ))}
        </TabsContent>

        <TabsContent value="actions" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Open Actions</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr className="border-b border-border/50">
                  {['Title', 'Status', 'Owner', 'Target', 'Priority', 'Due'].map(h => (
                    <th key={h} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {actions.data.map(a => (
                    <tr key={a.id} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                      <td className="px-3 py-2.5 text-xs text-foreground">{a.title}</td>
                      <td className="px-3 py-2.5"><StatusPill status={a.status} /></td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{a.owner}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{a.target}</td>
                      <td className="px-3 py-2.5"><span className={`text-[10px] px-2 py-0.5 rounded border font-medium capitalize ${priorityStyle[a.priority]}`}>{a.priority}</span></td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{a.dueDate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="operations" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <RefreshCw className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Recent Automated Operations</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="space-y-2">
              {operations.data.map((op, i) => (
                <motion.div key={op.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.03 }}
                  className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors">
                  <div className="flex items-center gap-3">
                    <StatusPill status={op.status === 'success' ? 'completed' : op.status === 'warning' ? 'warning' : 'error'} />
                    <div>
                      <p className="text-xs font-medium text-foreground font-mono">{op.operation}</p>
                      <p className="text-[10px] text-muted-foreground">{op.detail}</p>
                    </div>
                  </div>
                  <div className="text-[10px] text-muted-foreground text-right">
                    <p>{(op.durationMs / 1000).toFixed(1)}s</p>
                    <p>{new Date(op.timestamp).toLocaleString()}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="telemetry" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Radio className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Event Log</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="space-y-1">
              {telemetry.map((t, i) => (
                <div key={i} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-secondary/20 transition-colors font-mono">
                  <div className="flex items-center gap-3">
                    <Radio className="w-3 h-3 text-muted-foreground" />
                    <span className="text-[10px] text-primary">{t.event}</span>
                    <span className="text-[10px] text-foreground">{t.tool}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-muted-foreground">{t.latency}</span>
                    <StatusPill status={t.status === 'ok' ? 'active' : t.status === 'warning' ? 'degraded' : 'inactive'} />
                    {t.ts && <span className="text-[10px] text-muted-foreground">{new Date(t.ts).toLocaleTimeString()}</span>}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="readiness" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Readiness by Target</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="space-y-2">
              {readiness.map(r => (
                <div key={r.target} className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors">
                  <div>
                    <p className="text-xs font-medium text-foreground">{r.target}</p>
                    <p className="text-[10px] text-muted-foreground">{r.detail}</p>
                  </div>
                  <StatusPill status={r.status === 'ready' ? 'active' : 'degraded'} />
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="mt-4" delay={0.1}>
            <h4 className="text-xs font-medium text-foreground mb-3">MCP Console State</h4>
            <div className="bg-secondary/20 rounded-lg p-4 space-y-1 text-[10px] text-muted-foreground font-mono">
              <p>mcp_version: 1.2.0</p>
              <p>transport: stdio</p>
              <p>tools_registered: {mcpTools.length}</p>
              <p>tools_active: {mcpTools.filter(t => t.status === 'active').length}</p>
              <p>fallback_mode: local</p>
              <p>sync_plans: 0 active</p>
              <p>last_drift_check: 2024-03-14T12:00:00Z</p>
              <p>drift_status: minor_drift (Technical Architecture Brief)</p>
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="search" className="mt-0">
          <GlassCard>
            <h3 className="text-sm font-medium text-foreground mb-4">Document Search via MCP</h3>
            <div className="flex items-center gap-2 mb-4">
              <Input placeholder="Semantic search query..." className="h-8 text-xs bg-secondary/30 border-border/50" />
              <Button size="sm" className="h-8 bg-primary text-primary-foreground hover:bg-primary/90 text-xs px-4">
                <Search className="w-3.5 h-3.5 mr-1" /> Search
              </Button>
            </div>
            <div className="text-center py-8">
              <Search className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">Enter a query to search indexed documents via MCP tools</p>
            </div>
          </GlassCard>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
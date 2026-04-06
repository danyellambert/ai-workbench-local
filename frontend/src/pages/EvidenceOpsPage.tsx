import { motion } from 'framer-motion';
import { Terminal, Activity, Search, Wrench, AlertTriangle, RefreshCw, Database, Radio } from 'lucide-react';
import { PageHeader, StatusPill, GlassCard } from '@/components/shared/ui-components';
import { mcpTools } from '@/lib/mock-data';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const telemetry = [
  { event: 'tool_call', tool: 'search_documents', latency: '340ms', status: 'ok', ts: '2024-03-15T10:30:00Z' },
  { event: 'tool_call', tool: 'list_open_actions', latency: '120ms', status: 'ok', ts: '2024-03-15T10:45:00Z' },
  { event: 'drift_check', tool: 'detect_repository_drift', latency: '2.4s', status: 'warning', ts: '2024-03-14T12:00:00Z' },
  { event: 'sync_plan', tool: 'register_external_sync', latency: '—', status: 'skipped', ts: '' },
  { event: 'auto_register', tool: 'auto_register', latency: '560ms', status: 'ok', ts: '2024-03-15T06:00:00Z' },
];

export default function EvidenceOpsPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="EvidenceOps MCP" description="Operational console for MCP tools, repository state and telemetry.">
        <Button variant="outline" className="h-9 px-4 text-xs border-border/50"><RefreshCw className="w-3.5 h-3.5 mr-2" /> Sync</Button>
      </PageHeader>

      {/* Status Cards */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'MCP Tools', value: mcpTools.length, color: 'text-primary' },
          { label: 'Active', value: mcpTools.filter(t => t.status === 'active').length, color: 'text-glow-success' },
          { label: 'Degraded', value: mcpTools.filter(t => t.status === 'degraded').length, color: 'text-glow-warning' },
          { label: 'Last Sync', value: '2h ago', color: 'text-muted-foreground' },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 text-center">
            <p className={`text-2xl font-semibold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
          </div>
        ))}
      </motion.div>

      <Tabs defaultValue="tools">
        <TabsList className="bg-secondary/30 border border-border/50 mb-4">
          <TabsTrigger value="tools" className="text-xs data-[state=active]:bg-secondary">MCP Tools</TabsTrigger>
          <TabsTrigger value="telemetry" className="text-xs data-[state=active]:bg-secondary">Telemetry</TabsTrigger>
          <TabsTrigger value="repository" className="text-xs data-[state=active]:bg-secondary">Repository</TabsTrigger>
          <TabsTrigger value="search" className="text-xs data-[state=active]:bg-secondary">Search</TabsTrigger>
        </TabsList>

        <TabsContent value="tools" className="mt-0 space-y-3">
          {mcpTools.map((tool, i) => (
            <motion.div key={tool.name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.04 }}
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

        <TabsContent value="telemetry" className="mt-0">
          <GlassCard>
            <h3 className="text-sm font-medium text-foreground mb-4">Event Log</h3>
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

        <TabsContent value="repository" className="mt-0">
          <GlassCard>
            <h3 className="text-sm font-medium text-foreground mb-4">Repository Summary</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                {[
                  { label: 'Total documents', value: '10' },
                  { label: 'Open actions', value: '4' },
                  { label: 'Last auto-register', value: '2024-03-15 06:00' },
                  { label: 'Drift status', value: 'Minor drift detected' },
                ].map(r => (
                  <div key={r.label} className="flex justify-between py-1.5 text-xs">
                    <span className="text-muted-foreground">{r.label}</span>
                    <span className="text-foreground">{r.value}</span>
                  </div>
                ))}
              </div>
              <div className="bg-secondary/20 rounded-lg p-4">
                <h4 className="text-xs font-medium text-foreground mb-2">Console State</h4>
                <div className="space-y-1 text-[10px] text-muted-foreground font-mono">
                  <p>mcp_version: 1.2.0</p>
                  <p>transport: stdio</p>
                  <p>tools_registered: 6</p>
                  <p>fallback_mode: local</p>
                  <p>sync_plans: 0 active</p>
                </div>
              </div>
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
              <p className="text-xs text-muted-foreground">Enter a query to search indexed documents</p>
            </div>
          </GlassCard>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}

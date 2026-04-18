import { motion } from 'framer-motion';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, Search, Wrench, RefreshCw, Radio, Shield, Clock, AlertTriangle, FolderSearch } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabEvidenceOpsPage, searchLabEvidenceOps } from '@/lib/ai-lab-data';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const priorityStyle: Record<string, string> = {
  high: 'bg-glow-error/10 text-glow-error border-glow-error/20',
  medium: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
  low: 'bg-muted text-muted-foreground border-border',
};

function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export default function EvidenceOpsPage() {
  const [searchInput, setSearchInput] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');

  const evidenceQuery = useQuery({
    queryKey: aiLabQueryKeys.evidenceOps,
    queryFn: getLabEvidenceOpsPage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const searchQuery = useQuery({
    queryKey: aiLabQueryKeys.evidenceSearch(submittedQuery),
    queryFn: () => searchLabEvidenceOps(submittedQuery),
    enabled: submittedQuery.trim().length > 0,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const data = evidenceQuery.data;
  const summary = data?.summary;

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="EvidenceOps / MCP"
        description="Operational governance console — tool health, automated operations, action tracking and repository readiness."
        operatorQuestion="Is operations/governance healthy and controllable?"
        badges={[
          { label: `${summary?.activeTools ?? 0}/${summary?.toolsTotal ?? 0} tools active`, variant: summary && summary.activeTools === summary.toolsTotal ? 'success' : 'warning' },
          { label: `${summary?.openActions ?? 0} open actions`, variant: (summary?.openActions ?? 0) > 0 ? 'warning' : 'success' },
          { label: `${summary?.repositoryDocumentCount ?? 0} corpus docs`, variant: 'default' },
        ]}
        dataSource={data?.meta.source}
      >
        <Button variant="outline" className="h-9 px-4 text-xs border-border/50" onClick={() => evidenceQuery.refetch()}>
          <RefreshCw className="w-3.5 h-3.5 mr-2" />
          Sync
        </Button>
      </AiLabSectionIntro>

      {evidenceQuery.isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            EvidenceOps now reflects repository, action-store and worklog state only. The Product API is unavailable, so mock governance panels are no longer shown.
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={5}
        metrics={[
          { label: 'MCP Tools', value: summary?.toolsTotal ?? '—', icon: Wrench, status: 'neutral' },
          { label: 'Active', value: summary?.activeTools ?? '—', icon: Activity, status: summary ? 'healthy' : 'neutral' },
          { label: 'Open Actions', value: summary?.openActions ?? '—', icon: AlertTriangle, status: (summary?.openActions ?? 0) > 0 ? 'warning' : 'healthy' },
          { label: 'Auto Ops', value: summary?.operationsCount ?? '—', icon: RefreshCw, status: 'neutral' },
          { label: 'Last Sync', value: summary?.lastSyncAt ? formatDateTime(summary.lastSyncAt) : '—', icon: Clock, status: 'neutral' },
        ]}
      />

      <Tabs defaultValue="tools">
        <TabsList className="bg-secondary/30 border border-border/50 mb-4">
          <TabsTrigger value="tools" className="text-xs data-[state=active]:bg-secondary">Tools</TabsTrigger>
          <TabsTrigger value="actions" className="text-xs data-[state=active]:bg-secondary">Open Actions</TabsTrigger>
          <TabsTrigger value="operations" className="text-xs data-[state=active]:bg-secondary">Auto Operations</TabsTrigger>
          <TabsTrigger value="telemetry" className="text-xs data-[state=active]:bg-secondary">Telemetry</TabsTrigger>
          <TabsTrigger value="readiness" className="text-xs data-[state=active]:bg-secondary">Readiness</TabsTrigger>
          <TabsTrigger value="search" className="text-xs data-[state=active]:bg-secondary">Search</TabsTrigger>
        </TabsList>

        <TabsContent value="tools" className="mt-0 space-y-3">
          {(data?.tools ?? []).map((tool, index) => (
            <motion.div
              key={tool.name}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + index * 0.04 }}
              className="glass rounded-xl p-4 hover:border-primary/20 transition-all duration-300"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-secondary/50 flex items-center justify-center">
                    <Wrench className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div>
                    <h4 className="text-xs font-medium text-foreground font-mono">{tool.name}</h4>
                    <p className="text-[10px] text-muted-foreground">{tool.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <StatusPill status={tool.status} />
                  {tool.lastCall ? <span className="text-[10px] text-muted-foreground">{new Date(tool.lastCall).toLocaleTimeString()}</span> : null}
                </div>
              </div>
            </motion.div>
          ))}
          {evidenceQuery.isLoading && !(data?.tools?.length ?? 0) ? <GlassCard><p className="text-xs text-muted-foreground">Loading tool inventory…</p></GlassCard> : null}
        </TabsContent>

        <TabsContent value="actions" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Open Actions</h3>
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border/50">
                    {['Title', 'Status', 'Owner', 'Target', 'Priority', 'Due'].map((heading) => (
                      <th key={heading} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data?.actions ?? []).map((action) => (
                    <tr key={action.id} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                      <td className="px-3 py-2.5 text-xs text-foreground">{action.title}</td>
                      <td className="px-3 py-2.5"><StatusPill status={action.status} /></td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{action.owner}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{action.target}</td>
                      <td className="px-3 py-2.5"><span className={`text-[10px] px-2 py-0.5 rounded border font-medium capitalize ${priorityStyle[action.priority]}`}>{action.priority}</span></td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{action.dueDate}</td>
                    </tr>
                  ))}
                  {evidenceQuery.isLoading && !(data?.actions?.length ?? 0) ? (
                    <tr>
                      <td colSpan={6} className="px-3 py-6 text-xs text-muted-foreground">Loading action inventory…</td>
                    </tr>
                  ) : null}
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
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-2">
              {(data?.operations ?? []).map((operation, index) => (
                <motion.div
                  key={operation.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + index * 0.03 }}
                  className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors gap-4"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <StatusPill status={operation.status === 'success' ? 'completed' : operation.status === 'warning' ? 'warning' : 'error'} />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-foreground font-mono">{operation.operation}</p>
                      <p className="text-[10px] text-muted-foreground">{operation.detail}</p>
                    </div>
                  </div>
                  <div className="text-[10px] text-muted-foreground text-right shrink-0">
                    <p>{(operation.durationMs / 1000).toFixed(1)}s</p>
                    <p>{formatDateTime(operation.timestamp)}</p>
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
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-1">
              {(data?.telemetry ?? []).map((item, index) => (
                <div key={`${item.event}-${index}`} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-secondary/20 transition-colors font-mono gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <Radio className="w-3 h-3 text-muted-foreground shrink-0" />
                    <span className="text-[10px] text-primary">{item.event}</span>
                    <span className="text-[10px] text-foreground truncate">{item.tool}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-[10px] text-muted-foreground">{item.latency}</span>
                    <StatusPill status={item.status === 'ok' ? 'active' : item.status === 'warning' ? 'degraded' : 'inactive'} />
                    {item.ts ? <span className="text-[10px] text-muted-foreground">{new Date(item.ts).toLocaleTimeString()}</span> : null}
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
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="space-y-2">
              {(data?.readiness ?? []).map((item) => (
                <div key={item.target} className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors gap-4">
                  <div>
                    <p className="text-xs font-medium text-foreground">{item.target}</p>
                    <p className="text-[10px] text-muted-foreground">{item.detail}</p>
                  </div>
                  <StatusPill status={item.status === 'ready' ? 'active' : 'degraded'} />
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="mt-4" delay={0.1}>
            <h4 className="text-xs font-medium text-foreground mb-3">EvidenceOps Local State</h4>
            <div className="bg-secondary/20 rounded-lg p-4 space-y-1 text-[10px] text-muted-foreground font-mono">
              <p>data_source: {data?.meta.source ?? '—'}</p>
              <p>repository_root: {summary?.repositoryRoot ?? '—'}</p>
              <p>repository_documents: {summary?.repositoryDocumentCount ?? 0}</p>
              <p>tools_registered: {summary?.toolsTotal ?? 0}</p>
              <p>tools_active: {summary?.activeTools ?? 0}</p>
              <p>open_actions: {summary?.openActions ?? 0}</p>
              <p>last_sync_at: {summary?.lastSyncAt ?? '—'}</p>
            </div>
            {data?.meta.notes?.length ? (
              <div className="mt-3 rounded-lg bg-secondary/20 p-3 text-[10px] text-muted-foreground">
                {data.meta.notes.join(' ')}
              </div>
            ) : null}
          </GlassCard>
        </TabsContent>

        <TabsContent value="search" className="mt-0">
          <GlassCard>
            <h3 className="text-sm font-medium text-foreground mb-4">Repository Search</h3>
            <form
              className="flex items-center gap-2 mb-4"
              onSubmit={(event) => {
                event.preventDefault();
                setSubmittedQuery(searchInput.trim());
              }}
            >
              <Input
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search the live EvidenceOps repository…"
                className="h-8 text-xs bg-secondary/30 border-border/50"
              />
              <Button size="sm" className="h-8 bg-primary text-primary-foreground hover:bg-primary/90 text-xs px-4" type="submit">
                <Search className="w-3.5 h-3.5 mr-1" />
                Search
              </Button>
            </form>

            {!submittedQuery ? (
              <div className="text-center py-8">
                <FolderSearch className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">Enter a query to search indexed repository documents via live backend search.</p>
              </div>
            ) : searchQuery.isLoading ? (
              <div className="text-center py-8 text-xs text-muted-foreground">Searching repository for “{submittedQuery}”…</div>
            ) : searchQuery.isError ? (
              <div className="text-center py-8 text-xs text-glow-warning">Search failed. The endpoint is unavailable right now.</div>
            ) : (
              <div className="space-y-2">
                <div className="text-[10px] text-muted-foreground mb-2">
                  {searchQuery.data?.results.length ?? 0} result(s) in {searchQuery.data?.repositoryRoot ?? summary?.repositoryRoot ?? 'repository'}
                </div>
                {(searchQuery.data?.results ?? []).length === 0 ? (
                  <div className="text-center py-8 text-xs text-muted-foreground">No repository document matched this query.</div>
                ) : (
                  (searchQuery.data?.results ?? []).map((result, index) => (
                    <motion.div
                      key={`${result.relativePath}-${index}`}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.05 + index * 0.03 }}
                      className="rounded-lg border border-border/40 bg-secondary/20 p-3"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">{result.title}</p>
                          <p className="text-[10px] text-muted-foreground break-all">{result.relativePath}</p>
                          <div className="flex items-center gap-3 mt-1 text-[10px] text-muted-foreground flex-wrap">
                            <span>{result.category ?? 'uncategorized'}</span>
                            <span>{typeof result.sizeKb === 'number' ? `${result.sizeKb.toFixed(1)} KB` : 'size n/a'}</span>
                            <span>{result.suffix ?? '—'}</span>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-[10px] text-primary font-medium">score {result.matchScore.toFixed(1)}</p>
                          <p className="text-[10px] text-muted-foreground">{formatDateTime(result.modifiedAt)}</p>
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            )}
          </GlassCard>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}

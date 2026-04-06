import { motion } from 'framer-motion';
import { ClipboardList, AlertTriangle, CheckCircle2, Clock, User, Sparkles } from 'lucide-react';
import { PageHeader, StatusPill, SeverityBadge, GlassCard } from '@/components/shared/ui-components';
import { actionItems } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const statusCols = ['open', 'in_progress', 'blocked', 'done'] as const;

export default function ActionPlanPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Action Plan & Evidence Review" description="Transform findings into actionable tasks with owners, timelines and evidence tracking.">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"><Sparkles className="w-3.5 h-3.5 mr-2" /> Generate Deck</Button>
      </PageHeader>

      {/* Summary */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Open', value: actionItems.filter(a => a.status === 'open').length, color: 'text-primary' },
          { label: 'In Progress', value: actionItems.filter(a => a.status === 'in_progress').length, color: 'text-glow-warning' },
          { label: 'Blocked', value: actionItems.filter(a => a.status === 'blocked').length, color: 'text-glow-error' },
          { label: 'Done', value: actionItems.filter(a => a.status === 'done').length, color: 'text-glow-success' },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 text-center">
            <p className={`text-2xl font-semibold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
          </div>
        ))}
      </motion.div>

      <Tabs defaultValue="kanban">
        <TabsList className="bg-secondary/30 border border-border/50 mb-4">
          <TabsTrigger value="kanban" className="text-xs data-[state=active]:bg-secondary">Board</TabsTrigger>
          <TabsTrigger value="table" className="text-xs data-[state=active]:bg-secondary">Table</TabsTrigger>
          <TabsTrigger value="timeline" className="text-xs data-[state=active]:bg-secondary">Timeline</TabsTrigger>
          <TabsTrigger value="evidence" className="text-xs data-[state=active]:bg-secondary">Evidence Gaps</TabsTrigger>
        </TabsList>

        <TabsContent value="kanban" className="mt-0">
          <div className="grid md:grid-cols-4 gap-3">
            {statusCols.map(status => (
              <div key={status} className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <StatusPill status={status} />
                  <span className="text-[10px] text-muted-foreground">({actionItems.filter(a => a.status === status).length})</span>
                </div>
                {actionItems.filter(a => a.status === status).map((item, i) => (
                  <motion.div key={item.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 + i * 0.04 }}
                    className="glass rounded-lg p-3 hover:border-primary/20 transition-all cursor-pointer">
                    <div className="flex items-start justify-between mb-2">
                      <SeverityBadge severity={item.priority} />
                    </div>
                    <h4 className="text-xs font-medium text-foreground mb-2 leading-relaxed">{item.title}</h4>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                      <User className="w-3 h-3" />{item.owner}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-1">
                      <Clock className="w-3 h-3" />{item.dueDate}
                    </div>
                  </motion.div>
                ))}
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="table" className="mt-0">
          <div className="glass rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border/50">
                  {['Task', 'Owner', 'Priority', 'Status', 'Due Date', 'Source'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {actionItems.map(item => (
                  <tr key={item.id} className="border-b border-border/30 hover:bg-secondary/20 transition-colors">
                    <td className="px-4 py-3 text-xs text-foreground max-w-[250px] truncate">{item.title}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{item.owner}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={item.priority} /></td>
                    <td className="px-4 py-3"><StatusPill status={item.status} /></td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{item.dueDate}</td>
                    <td className="px-4 py-3 text-[10px] text-muted-foreground font-mono">{item.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="timeline" className="mt-0">
          <GlassCard>
            <div className="space-y-4">
              {actionItems.sort((a, b) => a.dueDate.localeCompare(b.dueDate)).map((item, i) => (
                <div key={item.id} className="flex items-start gap-4">
                  <div className="flex flex-col items-center">
                    <div className={`w-3 h-3 rounded-full ${
                      item.status === 'done' ? 'bg-glow-success' :
                      item.status === 'blocked' ? 'bg-glow-error' :
                      item.status === 'in_progress' ? 'bg-glow-warning' : 'bg-primary'
                    }`} />
                    {i < actionItems.length - 1 && <div className="w-px h-8 bg-border mt-1" />}
                  </div>
                  <div className="pb-4 flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-foreground">{item.title}</span>
                      <SeverityBadge severity={item.priority} />
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                      <span>{item.owner}</span>
                      <span>Due: {item.dueDate}</span>
                      <StatusPill status={item.status} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="evidence" className="mt-0">
          <GlassCard>
            <h3 className="text-sm font-medium text-foreground mb-4">Evidence Gaps Assessment</h3>
            <div className="space-y-3">
              {actionItems.map(item => (
                <div key={item.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/20">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground truncate">{item.title}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{item.evidence}</p>
                  </div>
                  <div className="flex items-center gap-2 ml-3">
                    {item.status === 'blocked' ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-glow-error/10 text-glow-error border border-glow-error/20">Needs Review</span>
                    ) : item.status === 'done' ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-glow-success/10 text-glow-success border border-glow-success/20">Sufficient</span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-glow-warning/10 text-glow-warning border border-glow-warning/20">Partial</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}

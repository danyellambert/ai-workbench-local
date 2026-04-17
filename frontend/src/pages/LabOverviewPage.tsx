import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { AlertTriangle, AlertCircle, Info, ArrowRight, Activity, FileText, Database, Cpu, ShieldCheck, BarChart3, GitBranch } from 'lucide-react';
import { AiLabSectionIntro } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { AI_LAB_ROUTES } from '@/lib/ai-lab-navigation';
import { getLabKPIs, getLabAlerts, getRuntimeSnapshot, getWorkflowCases } from '@/lib/ai-lab-data';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { PieChart, Pie, Cell } from 'recharts';

const kpis = getLabKPIs();
const alerts = getLabAlerts();
const runtime = getRuntimeSnapshot();
const cases = getWorkflowCases();

// Route distribution
const routeCounts = cases.data.reduce<Record<string, number>>((acc, c) => { acc[c.route] = (acc[c.route] || 0) + 1; return acc; }, {});
const routeData = Object.entries(routeCounts).map(([route, count]) => ({ name: route, value: count }));
const routeColors = ['hsl(217, 91%, 60%)', 'hsl(142, 71%, 45%)', 'hsl(38, 92%, 50%)', 'hsl(0, 84%, 60%)'];
const reviewRate = Math.round((cases.data.filter(c => c.needsReview).length / cases.data.length) * 100);

const routeChartConfig = {
  direct: { label: 'Direct', color: routeColors[0] },
  langgraph: { label: 'LangGraph', color: routeColors[1] },
  fallback: { label: 'Fallback', color: routeColors[2] },
};

const severityIcon: Record<string, React.ElementType> = { critical: AlertCircle, warning: AlertTriangle, info: Info };
const severityStyle: Record<string, string> = {
  critical: 'border-glow-error/30 bg-glow-error/5',
  warning: 'border-glow-warning/30 bg-glow-warning/5',
  info: 'border-border/50 bg-secondary/20',
};

export default function LabOverviewPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="AI Engineering Operating Console"
        description="Unified view of runtime health, quality signals, active alerts and operational readiness."
        operatorQuestion="What needs attention right now?"
        badges={[
          { label: 'AI Lab', variant: 'default' },
          { label: runtime.data.vectorBackendStatus === 'healthy' ? 'Runtime Healthy' : 'Runtime Degraded', variant: runtime.data.vectorBackendStatus === 'healthy' ? 'success' : 'warning' },
          { label: `${runtime.data.indexedDocumentCount} docs indexed`, variant: 'default' },
        ]}
        dataSource={kpis.meta.source}
      />

      {/* Health Strip */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        className="glass rounded-xl p-3 px-5 mb-6 flex items-center gap-6 text-[11px] overflow-x-auto">
        <div className="flex items-center gap-2 shrink-0">
          <span className="w-2 h-2 rounded-full bg-glow-success animate-pulse" />
          <span className="text-muted-foreground">Runtime</span>
          <span className="text-foreground font-medium">{runtime.data.generationProvider} · {runtime.data.generationModel.split(':')[0]}</span>
        </div>
        <div className="w-px h-4 bg-border/50" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-muted-foreground">Vector</span>
          <StatusPill status={runtime.data.vectorBackendStatus === 'healthy' ? 'active' : 'degraded'} />
        </div>
        <div className="w-px h-4 bg-border/50" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-muted-foreground">Context</span>
          <span className="text-foreground font-medium">{Math.round(runtime.data.contextPressure * 100)}%</span>
        </div>
        <div className="w-px h-4 bg-border/50" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-muted-foreground">Ingestion</span>
          <StatusPill status={runtime.data.ingestionHealth === 'healthy' ? 'active' : 'warning'} />
        </div>
      </motion.div>

      {/* KPIs */}
      <AiLabMetricGrid
        columns={6}
        metrics={kpis.data.map(k => ({
          label: k.label,
          value: k.value,
          status: k.status,
          trend: k.trend,
          icon: k.label.includes('Document') ? FileText : k.label.includes('Chunk') ? Database : k.label.includes('Run') ? Activity : k.label.includes('MCP') ? Cpu : k.label.includes('Eval') ? ShieldCheck : BarChart3,
        }))}
      />

      <div className="grid lg:grid-cols-3 gap-4 mb-6">
        {/* Alerts */}
        <div className="lg:col-span-2">
          <GlassCard delay={0.15}>
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-4 h-4 text-glow-warning" />
              <h3 className="text-sm font-medium text-foreground">Active Alerts</h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-warning/10 text-glow-warning border border-glow-warning/20">
                {alerts.data.length}
              </span>
            </div>
            <div className="space-y-2">
              {alerts.data.map((alert, i) => {
                const Icon = severityIcon[alert.severity] || Info;
                return (
                  <motion.div key={alert.id} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + i * 0.04 }}
                    className={`flex items-start gap-3 p-3 rounded-lg border ${severityStyle[alert.severity]}`}>
                    <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${
                      alert.severity === 'critical' ? 'text-glow-error' : alert.severity === 'warning' ? 'text-glow-warning' : 'text-muted-foreground'
                    }`} />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-foreground">{alert.title}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">{alert.detail}</p>
                    </div>
                    <span className="text-[9px] text-muted-foreground/50 shrink-0">{alert.source}</span>
                  </motion.div>
                );
              })}
            </div>
          </GlassCard>
        </div>

        {/* Routing Distribution */}
        <GlassCard delay={0.18}>
          <div className="flex items-center gap-2 mb-3">
            <GitBranch className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Routing Distribution</h3>
          </div>
          <div className="h-[140px]">
            <ChartContainer config={routeChartConfig} className="w-full h-full">
              <PieChart>
                <Pie data={routeData} cx="50%" cy="50%" innerRadius={35} outerRadius={55} paddingAngle={3} dataKey="value">
                  {routeData.map((_, idx) => (
                    <Cell key={idx} fill={routeColors[idx % routeColors.length]} />
                  ))}
                </Pie>
                <ChartTooltip content={<ChartTooltipContent />} />
              </PieChart>
            </ChartContainer>
          </div>
          <div className="space-y-1.5 mt-2">
            {routeData.map((d, i) => (
              <div key={d.name} className="flex items-center justify-between text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: routeColors[i] }} />
                  <span className="text-muted-foreground capitalize">{d.name}</span>
                </div>
                <span className="text-foreground font-medium">{d.value}</span>
              </div>
            ))}
            <div className="pt-1.5 border-t border-border/30 flex justify-between text-[10px]">
              <span className="text-muted-foreground">Review rate</span>
              <span className={`font-medium ${reviewRate > 40 ? 'text-glow-warning' : 'text-glow-success'}`}>{reviewRate}%</span>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Navigation Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
        {AI_LAB_ROUTES.filter(r => r.key !== 'overview').map((route, i) => {
          const Icon = route.icon;
          return (
            <motion.div key={route.key} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 + i * 0.04 }}>
              <Link to={route.path} className="glass rounded-xl p-4 block hover:border-primary/30 transition-all duration-300 group h-full">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Icon className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <h4 className="text-xs font-medium text-foreground">{route.label}</h4>
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed">{route.description}</p>
                <div className="flex items-center gap-1 mt-3 text-[10px] text-primary/60 group-hover:text-primary transition-colors">
                  <span>Open</span><ArrowRight className="w-3 h-3" />
                </div>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

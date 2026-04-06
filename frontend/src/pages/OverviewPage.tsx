import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  LayoutDashboard, FileText, ArrowRight, Sparkles, Activity,
  Shield, GitCompare, ClipboardList, UserCheck, FileOutput,
  Play, Layers, BarChart3, Zap, Database
} from 'lucide-react';
import { MetricCard, StatusPill, GlassCard } from '@/components/shared/ui-components';
import { systemStats, workflowRuns, artifacts } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';

const stagger = { animate: { transition: { staggerChildren: 0.06 } } };
const item = { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] } } };

const workflows = [
  { title: 'Document Review', desc: 'Review documents for risks, gaps and findings with grounded evidence', icon: Shield, path: '/app/workflows/document-review', color: 'primary' },
  { title: 'Policy Comparison', desc: 'Compare contracts side-by-side with impact analysis and recommendations', icon: GitCompare, path: '/app/workflows/comparison', color: 'accent' },
  { title: 'Action Plan', desc: 'Transform findings into owners, tasks, timelines and operational handoff', icon: ClipboardList, path: '/app/workflows/action-plan', color: 'success' },
  { title: 'Candidate Review', desc: 'Analyze CVs for strengths, gaps, seniority signals and hiring recommendation', icon: UserCheck, path: '/app/workflows/candidate-review', color: 'warning' },
];

const demoScenarios = [
  { label: 'Run Document Risk Review', path: '/app/workflows/document-review', icon: Play },
  { label: 'Compare Contract Versions', path: '/app/workflows/comparison', icon: GitCompare },
  { label: 'Build Action Plan From Findings', path: '/app/workflows/action-plan', icon: ClipboardList },
  { label: 'Review Candidate CV', path: '/app/workflows/candidate-review', icon: UserCheck },
];

export default function OverviewPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto space-y-8" variants={stagger} initial="initial" animate="animate">
      {/* Hero */}
      <motion.div variants={item} className="relative overflow-hidden rounded-2xl border border-border/50 bg-gradient-to-br from-card via-card to-surface-2 p-8 lg:p-10">
        <div className="absolute top-0 right-0 w-[400px] h-[400px] opacity-[0.06] pointer-events-none"
          style={{ background: 'radial-gradient(circle, hsl(187 90% 70%), transparent 70%)' }} />
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-primary tracking-wide uppercase">AI Workbench Local</span>
          </div>
          <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-foreground max-w-2xl leading-tight">
            Turn documents into<br />
            <span className="text-gradient-hero">grounded decisions</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-3 max-w-lg leading-relaxed">
            Review, compare and operationalize enterprise documents with AI-powered evidence workflows.
            From ingestion to recommendation to executive artifact.
          </p>
          <div className="flex items-center gap-3 mt-6">
            <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs font-medium">
              <Link to="/app/workflows">Explore Workflows <ArrowRight className="ml-2 w-3.5 h-3.5" /></Link>
            </Button>
            <Button variant="outline" asChild className="h-9 px-4 text-xs border-border/50 text-muted-foreground hover:text-foreground">
              <Link to="/app/documents">Document Library</Link>
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Metrics */}
      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Indexed Documents" value={systemStats.indexedDocuments} icon={FileText} glowColor="primary" delay={0.1} />
        <MetricCard label="Total Chunks" value={systemStats.totalChunks.toLocaleString()} icon={Database} glowColor="accent" delay={0.15} />
        <MetricCard label="Completed Runs" value={systemStats.completedRuns} icon={Activity} glowColor="success" trend="+3 today" delay={0.2} />
        <MetricCard label="Artifacts Generated" value={systemStats.artifactsGenerated} icon={FileOutput} glowColor="warning" delay={0.25} />
      </motion.div>

      {/* Workflow Cards */}
      <motion.div variants={item}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-foreground">Decision Workflows</h2>
          <Link to="/app/workflows" className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1">
            View catalog <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
          {workflows.map((wf, i) => (
            <Link key={wf.title} to={wf.path}>
              <motion.div
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.06, duration: 0.4 }}
                className="glass rounded-xl p-4 h-full group hover:border-primary/30 transition-all duration-300 cursor-pointer"
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 ${
                  wf.color === 'primary' ? 'bg-primary/10 text-primary' :
                  wf.color === 'accent' ? 'bg-accent/10 text-accent' :
                  wf.color === 'success' ? 'bg-glow-success/10 text-glow-success' :
                  'bg-glow-warning/10 text-glow-warning'
                }`}>
                  <wf.icon className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-medium text-foreground mb-1">{wf.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{wf.desc}</p>
                <div className="mt-3 flex items-center gap-1 text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                  Launch <ArrowRight className="w-3 h-3" />
                </div>
              </motion.div>
            </Link>
          ))}
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-3 gap-3">
        {/* Recent Runs */}
        <GlassCard className="lg:col-span-2" delay={0.4}>
          <h3 className="text-sm font-medium text-foreground mb-4">Recent Runs</h3>
          <div className="space-y-2">
            {workflowRuns.slice(0, 5).map(run => (
              <div key={run.id} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-secondary/30 transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusPill status={run.status} />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{run.workflow}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{run.documents.join(', ')}</p>
                  </div>
                </div>
                <div className="text-right shrink-0 ml-3">
                  <p className="text-[10px] text-muted-foreground">{run.duration}</p>
                  {run.findings && <p className="text-[10px] text-muted-foreground">{run.findings} findings</p>}
                </div>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Demo Scenarios */}
        <GlassCard delay={0.45}>
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Quick Launch</h3>
          </div>
          <div className="space-y-2">
            {demoScenarios.map(sc => (
              <Link key={sc.label} to={sc.path}
                className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-secondary/40 transition-colors group cursor-pointer">
                <div className="w-7 h-7 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
                  <sc.icon className="w-3.5 h-3.5 text-primary" />
                </div>
                <span className="text-xs text-foreground group-hover:text-primary transition-colors">{sc.label}</span>
              </Link>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* AI Lab Teaser + Artifacts */}
      <div className="grid lg:grid-cols-2 gap-3">
        <GlassCard delay={0.5}>
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-medium text-foreground">AI Engineering Lab</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-4">Explore the technical foundation: RAG chat, structured outputs, model benchmarks and operational tooling.</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Chat with RAG', path: '/app/lab/chat', icon: LayoutDashboard },
              { label: 'Structured Outputs', path: '/app/lab/structured', icon: Layers },
              { label: 'Model Comparison', path: '/app/lab/models', icon: BarChart3 },
              { label: 'EvidenceOps MCP', path: '/app/lab/evidenceops', icon: Activity },
            ].map(l => (
              <Link key={l.path} to={l.path} className="flex items-center gap-2 py-2 px-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors text-xs text-muted-foreground hover:text-foreground">
                <l.icon className="w-3.5 h-3.5" />{l.label}
              </Link>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.55}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FileOutput className="w-4 h-4 text-glow-warning" />
              <h3 className="text-sm font-medium text-foreground">Recent Artifacts</h3>
            </div>
            <Link to="/deck-center" className="text-xs text-primary hover:text-primary/80 transition-colors">View all</Link>
          </div>
          <div className="space-y-2">
            {artifacts.slice(0, 4).map(a => (
              <div key={a.id} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-secondary/30 transition-colors">
                <div className="flex items-center gap-2 min-w-0">
                  <StatusPill status={a.status} />
                  <span className="text-xs text-foreground truncate">{a.name}</span>
                </div>
                <span className="text-[10px] text-muted-foreground shrink-0 ml-2">{a.size}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}

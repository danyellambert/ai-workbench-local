import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Shield, GitCompare, ClipboardList, UserCheck, ArrowRight, FileOutput, Sparkles } from 'lucide-react';
import { PageHeader } from '@/components/shared/ui-components';

const workflows = [
  {
    title: 'Document Review', icon: Shield, path: '/app/workflows/document-review',
    headline: 'Deep-dive risk and compliance analysis',
    description: 'Review any document for risks, gaps, compliance issues and opportunities. Produces grounded findings with evidence trails and executive-ready artifacts.',
    inputs: ['1+ documents'], outputs: ['Findings report', 'Evidence map', 'Risk matrix'], deckReady: true,
    color: 'from-primary/20 to-primary/5', iconBg: 'bg-primary/15 text-primary',
  },
  {
    title: 'Policy Comparison', icon: GitCompare, path: '/app/workflows/comparison',
    headline: 'Side-by-side contract intelligence',
    description: 'Compare two or more documents to surface critical differences, assess business impact, and generate data-driven recommendations for decision makers.',
    inputs: ['2+ documents'], outputs: ['Diff analysis', 'Impact assessment', 'Recommendation'], deckReady: true,
    color: 'from-accent/20 to-accent/5', iconBg: 'bg-accent/15 text-accent',
  },
  {
    title: 'Action Plan', icon: ClipboardList, path: '/app/workflows/action-plan',
    headline: 'From insight to operational handoff',
    description: 'Transform document findings into actionable work: owners, tasks, deadlines, evidence gaps and follow-up tracking for operational execution.',
    inputs: ['Findings from review'], outputs: ['Action items', 'Evidence pack', 'Timeline'], deckReady: true,
    color: 'from-glow-success/20 to-glow-success/5', iconBg: 'bg-glow-success/15 text-glow-success',
  },
  {
    title: 'Candidate Review', icon: UserCheck, path: '/app/workflows/candidate-review',
    headline: 'AI-powered hiring intelligence',
    description: 'Analyze candidate CVs for strengths, gaps, seniority signals and cultural fit. Produces structured evaluation with hiring recommendation and confidence scoring.',
    inputs: ['1 CV document'], outputs: ['Profile analysis', 'Scorecard', 'Recommendation'], deckReady: true,
    color: 'from-glow-warning/20 to-glow-warning/5', iconBg: 'bg-glow-warning/15 text-glow-warning',
  },
];

export default function WorkflowCatalogPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Decision Workflows" description="AI-powered workflows that transform documents into grounded decisions and executive artifacts." />

      {/* Transversal capability banner */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="glass rounded-xl p-4 mb-8 flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-glow-warning/10 flex items-center justify-center shrink-0">
          <FileOutput className="w-5 h-5 text-glow-warning" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="text-sm font-medium text-foreground">Executive Deck Generation</h3>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-medium">Transversal</span>
          </div>
          <p className="text-xs text-muted-foreground">Every workflow can produce executive-ready PPTX decks, JSON payloads and structured review artifacts.</p>
        </div>
        <Link to="/app/deck-center" className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 shrink-0">
          Deck Center <ArrowRight className="w-3 h-3" />
        </Link>
      </motion.div>

      {/* Workflow Cards */}
      <div className="space-y-4">
        {workflows.map((wf, i) => (
          <motion.div key={wf.title} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + i * 0.08, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}>
            <Link to={wf.path} className="block">
              <div className={`glass rounded-xl p-6 group hover:border-primary/30 transition-all duration-300 cursor-pointer bg-gradient-to-r ${wf.color}`}>
                <div className="flex items-start gap-5">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${wf.iconBg}`}>
                    <wf.icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-semibold text-foreground">{wf.title}</h3>
                      {wf.deckReady && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-warning/10 text-glow-warning border border-glow-warning/20 font-medium flex items-center gap-1">
                          <Sparkles className="w-2.5 h-2.5" /> Deck Ready
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mb-1">{wf.headline}</p>
                    <p className="text-xs text-muted-foreground/70 leading-relaxed max-w-2xl">{wf.description}</p>
                    <div className="flex items-center gap-6 mt-4">
                      <div>
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-medium">Inputs</span>
                        <div className="flex items-center gap-1 mt-1">
                          {wf.inputs.map(inp => (
                            <span key={inp} className="text-[10px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground">{inp}</span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-medium">Outputs</span>
                        <div className="flex items-center gap-1 mt-1">
                          {wf.outputs.map(out => (
                            <span key={out} className="text-[10px] px-2 py-0.5 rounded-md bg-primary/5 text-primary/80">{out}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors shrink-0 mt-3 group-hover:translate-x-1 duration-200" />
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { Shield, GitCompare, ClipboardList, UserCheck, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const workflows = [
  {
    title: 'Document Review',
    desc: 'Systematically analyze contracts, policies and reports for risks, gaps and compliance issues.',
    benefit: 'Surface critical findings with evidence-backed severity ratings',
    icon: Shield,
    gradient: 'from-primary/20 to-primary/5',
    borderGlow: 'hover:shadow-[0_0_30px_-8px_hsl(var(--primary)/0.3)]',
  },
  {
    title: 'Policy Comparison',
    desc: 'Compare document versions side-by-side with clause-level impact analysis and delta mapping.',
    benefit: 'Identify every material change across contract iterations',
    icon: GitCompare,
    gradient: 'from-accent/20 to-accent/5',
    borderGlow: 'hover:shadow-[0_0_30px_-8px_hsl(var(--accent)/0.3)]',
  },
  {
    title: 'Action Plan',
    desc: 'Transform review findings into structured action items with owners, timelines and priorities.',
    benefit: 'Bridge analysis to execution with decision-ready outputs',
    icon: ClipboardList,
    gradient: 'from-glow-success/20 to-glow-success/5',
    borderGlow: 'hover:shadow-[0_0_30px_-8px_hsl(var(--glow-success)/0.3)]',
  },
  {
    title: 'Candidate Review',
    desc: 'Analyze CVs for strengths, gaps, seniority signals and hiring recommendations grounded in evidence.',
    benefit: 'Structured candidate assessment with traceable reasoning',
    icon: UserCheck,
    gradient: 'from-glow-warning/20 to-glow-warning/5',
    borderGlow: 'hover:shadow-[0_0_30px_-8px_hsl(var(--glow-warning)/0.3)]',
  },
];

export default function LandingWorkflows() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section className="relative py-32 px-6" ref={ref}>
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium mb-4">Decision Workflows</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Four workflows. One grounded system.
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
            Each workflow is purpose-built to extract structured, evidence-backed insights from your documents.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-4">
          {workflows.map((wf, i) => (
            <motion.div
              key={wf.title}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.15 * i }}
            >
              <Link to="/app/workflows" className="block h-full">
                <div className={`group relative h-full rounded-2xl border border-border/50 bg-gradient-to-br ${wf.gradient} backdrop-blur-sm p-7 transition-all duration-500 hover:border-border ${wf.borderGlow}`}>
                  <div className="flex items-start gap-4">
                    <div className="w-11 h-11 rounded-xl bg-card/60 border border-border/40 flex items-center justify-center shrink-0">
                      <wf.icon className="w-5 h-5 text-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-base font-semibold text-foreground mb-2">{wf.title}</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed mb-3">{wf.desc}</p>
                      <p className="text-xs text-primary/80 font-medium">{wf.benefit}</p>
                    </div>
                  </div>
                  <div className="mt-5 flex items-center gap-1.5 text-xs text-primary opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-1 group-hover:translate-y-0">
                    Launch workflow <ArrowRight className="w-3 h-3" />
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

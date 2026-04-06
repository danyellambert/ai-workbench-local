import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { FileOutput, FileJson, ClipboardCheck, Presentation, FileText, Download } from 'lucide-react';

const artifacts = [
  { icon: ClipboardCheck, title: 'Structured Findings', desc: 'Typed findings with severity, confidence, source references and actionable recommendations.', preview: '{ severity: "critical", confidence: 0.94 }' },
  { icon: FileText, title: 'Review Outputs', desc: 'Complete document review reports with grounded analysis and categorized risk assessments.', preview: 'gaps · risks · compliance' },
  { icon: Presentation, title: 'Executive Decks', desc: 'Auto-generated presentation decks ready for board reviews, stakeholder meetings and audits.', preview: '.pptx · branded · export-ready' },
  { icon: FileJson, title: 'JSON Exports', desc: 'Machine-readable structured outputs for downstream integrations and data pipelines.', preview: '{ workflow, findings, actions }' },
  { icon: ClipboardCheck, title: 'Action Plans', desc: 'Operational handoff documents with owners, timelines, priorities and completion criteria.', preview: 'owner · priority · deadline' },
  { icon: Download, title: 'Decision Materials', desc: 'Consolidated packages combining analysis, evidence and recommendations for decision-makers.', preview: 'analysis + evidence + recs' },
];

export default function LandingArtifacts() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="relative py-32 px-6" ref={ref}>
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium mb-4">Outputs & Artifacts</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight max-w-2xl mx-auto">
            Not just answers. Decision-ready artifacts.
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto">
            Every workflow produces structured, exportable outputs ready for stakeholders, audits and operational handoff.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {artifacts.map((art, i) => (
            <motion.div
              key={art.title}
              initial={{ opacity: 0, y: 25 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: 0.08 * i }}
              className="group rounded-2xl border border-border/40 bg-card/25 backdrop-blur-sm p-6 hover:border-primary/25 transition-all duration-500"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                  <art.icon className="w-4 h-4 text-primary" />
                </div>
                <h3 className="text-sm font-semibold text-foreground">{art.title}</h3>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">{art.desc}</p>
              <div className="px-3 py-2 rounded-lg bg-background/60 border border-border/30">
                <code className="text-[10px] font-mono text-primary/70">{art.preview}</code>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

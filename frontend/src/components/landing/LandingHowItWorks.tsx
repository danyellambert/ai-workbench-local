import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { Upload, Search, Workflow, FileOutput } from 'lucide-react';

const steps = [
  { num: '01', title: 'Upload Documents', desc: 'Ingest contracts, reports, policies or CVs. PDFs, DOCX, XLSX — extracted, chunked and embedded automatically.', icon: Upload },
  { num: '02', title: 'Ground Context', desc: 'Documents are semantically indexed with vector search, reranking and evidence linking for high-fidelity retrieval.', icon: Search },
  { num: '03', title: 'Run Workflow', desc: 'Select a decision workflow — review, comparison, action plan or candidate assessment. The AI processes with structured prompts.', icon: Workflow },
  { num: '04', title: 'Generate Outputs', desc: 'Receive structured findings, recommendations, action items and executive deck exports — all grounded and traceable.', icon: FileOutput },
];

export default function LandingHowItWorks() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="relative py-32 px-6" ref={ref}>
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium mb-4">How It Works</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            From documents to decisions in four steps.
          </h2>
        </motion.div>

        <div className="relative">
          {/* Connector line */}
          <div className="absolute left-[27px] md:left-1/2 md:-translate-x-px top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-border to-transparent hidden sm:block" />

          <div className="space-y-12 md:space-y-16">
            {steps.map((step, i) => (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, x: i % 2 === 0 ? -40 : 40 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.5, delay: 0.2 * i }}
                className={`relative flex items-start gap-6 md:gap-0 ${i % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'}`}
              >
                {/* Content */}
                <div className={`flex-1 ${i % 2 === 0 ? 'md:pr-16 md:text-right' : 'md:pl-16'}`}>
                  <div className={`inline-flex flex-col ${i % 2 === 0 ? 'md:items-end' : 'md:items-start'}`}>
                    <span className="text-xs font-mono text-primary/60 mb-2">{step.num}</span>
                    <h3 className="text-lg font-semibold text-foreground mb-2">{step.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed max-w-sm">{step.desc}</p>
                  </div>
                </div>

                {/* Node */}
                <div className="absolute left-0 md:left-1/2 md:-translate-x-1/2 w-[54px] h-[54px] rounded-2xl bg-card border border-border/60 flex items-center justify-center z-10 shadow-[0_0_20px_-5px_hsl(var(--primary)/0.2)]">
                  <step.icon className="w-5 h-5 text-primary" />
                </div>

                {/* Spacer for other side */}
                <div className="flex-1 hidden md:block" />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

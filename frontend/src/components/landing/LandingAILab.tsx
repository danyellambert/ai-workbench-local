import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { MessageSquare, Layers, BarChart3, Terminal } from 'lucide-react';

const labFeatures = [
  { icon: MessageSquare, title: 'Chat with RAG', desc: 'Conversational interface grounded in your indexed document corpus with citation-linked responses.' },
  { icon: Layers, title: 'Structured Outputs', desc: 'Define schemas and extract typed, validated data from documents with JSON-mode generation.' },
  { icon: BarChart3, title: 'Model Comparison', desc: 'Benchmark models across latency, groundedness, adherence and use-case fit with side-by-side evaluation.' },
  { icon: Terminal, title: 'EvidenceOps MCP', desc: 'Model Context Protocol server for programmatic access to retrieval, grounding and workflow orchestration.' },
];

export default function LandingAILab() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="relative py-32 px-6" ref={ref}>
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-14"
        >
          <p className="text-xs uppercase tracking-[0.2em] text-accent font-medium mb-4">AI Engineering Lab</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight max-w-xl">
            Technical depth behind the product.
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg">
            The product solves the business problem. The AI Lab provides the engineering foundation — 
            observability, control and reliability for every decision.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 gap-4">
          {labFeatures.map((feat, i) => (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 25 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: 0.12 * i }}
              className="group flex items-start gap-4 rounded-2xl border border-border/40 bg-card/20 backdrop-blur-sm p-6 hover:border-accent/30 transition-all duration-500 hover:shadow-[0_0_25px_-8px_hsl(var(--accent)/0.15)]"
            >
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center shrink-0 group-hover:bg-accent/15 transition-colors">
                <feat.icon className="w-5 h-5 text-accent" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-1.5">{feat.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{feat.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

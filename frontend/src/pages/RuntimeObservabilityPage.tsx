import { motion } from 'framer-motion';
import { Server, Cpu, Database, FileSearch, Activity, Gauge, HardDrive, Layers, GitBranch } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { getRuntimeSnapshot } from '@/lib/ai-lab-data';
import { Progress } from '@/components/ui/progress';

const { data: rt, meta } = getRuntimeSnapshot();

export default function RuntimeObservabilityPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Runtime & Observability"
        description="Full runtime configuration, resource health and diagnostic summary for the AI pipeline."
        operatorQuestion="Is the runtime healthy and cost-controlled?"
        badges={[
          { label: rt.vectorBackendStatus === 'healthy' ? 'All Systems Operational' : 'Degraded', variant: rt.vectorBackendStatus === 'healthy' ? 'success' : 'warning' },
          { label: `${rt.indexedDocumentCount} docs`, variant: 'default' },
          { label: rt.retrievalStrategy, variant: 'default' },
        ]}
        dataSource={meta.source}
      />

      <AiLabMetricGrid columns={4} metrics={[
        { label: 'Context Pressure', value: `${Math.round(rt.contextPressure * 100)}%`, status: rt.contextPressure > 0.8 ? 'warning' : 'healthy', icon: Gauge },
        { label: 'Indexed Documents', value: rt.indexedDocumentCount, status: 'healthy', icon: FileSearch },
        { label: 'Vector Backend', value: rt.vectorBackend, status: rt.vectorBackendStatus === 'healthy' ? 'healthy' : 'warning', icon: Database },
        { label: 'Ingestion Health', value: rt.ingestionHealth === 'healthy' ? 'Healthy' : 'Warning', status: rt.ingestionHealth === 'healthy' ? 'healthy' : 'warning', icon: Activity },
      ]} />

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        {/* Generation */}
        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Generation Configuration</h3>
            <DataSourceBadge source="derived" />
          </div>
          <div className="space-y-2.5 text-xs">
            {[
              ['Provider', rt.generationProvider],
              ['Model', rt.generationModel],
              ['Prompt Profile', rt.promptProfile],
              ['Context Window', rt.contextWindowMode],
              ['Resolved Context', `${rt.resolvedContext.toLocaleString()} tokens`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1.5 border-b border-border/20 last:border-0">
                <span className="text-muted-foreground">{k}</span>
                <span className="text-foreground font-mono text-[11px]">{v}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Retrieval */}
        <GlassCard delay={0.15}>
          <div className="flex items-center gap-2 mb-4">
            <FileSearch className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Retrieval Configuration</h3>
            <DataSourceBadge source="derived" />
          </div>
          <div className="space-y-2.5 text-xs">
            {[
              ['Embedding Provider', rt.embeddingProvider],
              ['Embedding Model', rt.embeddingModel],
              ['Strategy', rt.retrievalStrategy],
              ['Chunk Size / Overlap', `${rt.chunkSize} / ${rt.chunkOverlap}`],
              ['Top-K', String(rt.topK)],
              ['Rerank Pool', String(rt.rerankPoolSize)],
              ['Lexical Weight', String(rt.rerankLexicalWeight)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1.5 border-b border-border/20 last:border-0">
                <span className="text-muted-foreground">{k}</span>
                <span className="text-foreground font-mono text-[11px]">{v}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Context Budget */}
      <GlassCard className="mb-6" delay={0.2}>
        <div className="flex items-center gap-2 mb-4">
          <Gauge className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Context Budget</h3>
          <DataSourceBadge source="derived" />
        </div>
        <div className="flex items-center gap-4 mb-2">
          <span className="text-xs text-muted-foreground">Used: {rt.contextBudgetUsed.toLocaleString()}</span>
          <span className="text-xs text-muted-foreground">Total: {rt.contextBudgetTotal.toLocaleString()}</span>
          <span className={`text-xs font-medium ${rt.contextPressure > 0.8 ? 'text-glow-warning' : 'text-glow-success'}`}>
            {Math.round(rt.contextPressure * 100)}%
          </span>
        </div>
        <Progress value={rt.contextPressure * 100} className="h-2 bg-secondary" />
        <p className="text-[10px] text-muted-foreground mt-2">
          {rt.contextPressure > 0.8
            ? 'Context budget is under pressure. Consider reducing top-k or chunk size.'
            : 'Context budget is within healthy limits.'}
        </p>
      </GlassCard>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Vector Backend */}
        <GlassCard delay={0.25}>
          <div className="flex items-center gap-2 mb-4">
            <HardDrive className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Vector Backend</h3>
            <StatusPill status={rt.vectorBackendStatus === 'healthy' ? 'active' : 'degraded'} />
          </div>
          <div className="space-y-2 text-xs">
            {[
              ['Backend', rt.vectorBackend],
              ['Status', rt.vectorBackendStatus],
              ['Indexed Documents', String(rt.indexedDocumentCount)],
              ['Total Chunks', '1,360'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1.5">
                <span className="text-muted-foreground">{k}</span>
                <span className="text-foreground">{v}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Diagnostics Summary */}
        <GlassCard delay={0.3}>
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Diagnostics Summary</h3>
            <DataSourceBadge source="mock" />
          </div>
          <div className="space-y-2 text-xs">
            {[
              ['OCR Backend', 'Tesseract (Surya fallback)'],
              ['PDF Extraction', 'pdf_plumber'],
              ['VLM Status', 'Not active'],
              ['Routing Mode', 'Confidence-threshold with LangGraph fallback'],
              ['Active Traces', '0'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1.5">
                <span className="text-muted-foreground">{k}</span>
                <span className="text-foreground">{v}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}

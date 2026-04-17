import { motion } from 'framer-motion';
import { Archive, Eye, FlaskConical, FileSearch, Layers, Cpu } from 'lucide-react';
import { AiLabSectionIntro } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { ArtifactExplorerPanel } from '@/components/ai-lab/ArtifactExplorerPanel';
import { GlassCard } from '@/components/shared/ui-components';
import { DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { getLabArtifacts } from '@/lib/ai-lab-data';

const artifacts = getLabArtifacts();

const diagnostics = [
  { label: 'OCR Quality', detail: 'Tesseract primary, Surya fallback', status: '6/7 indexed docs clean · 1 failure (Technical Architecture Brief pp. 12-15)', health: 'warning' as const },
  { label: 'PDF Extraction', detail: 'pdf_plumber with table detection', status: 'Active — 7 documents processed', health: 'healthy' as const },
  { label: 'VLM Processing', detail: 'Not active — no image-heavy docs in current set', status: 'Standby', health: 'neutral' as const },
  { label: 'Embedding Drift', detail: 'nomic-embed-text v1.5 — 1,360 chunks indexed', status: 'No drift detected', health: 'healthy' as const },
  { label: 'Reranking', detail: 'Cross-encoder with BM25 fusion (hybrid_rerank)', status: 'Operational — production strategy', health: 'healthy' as const },
];

export default function AdvancedExperimentsPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Experiments & Artifacts"
        description="Technical evidence archive, experimentation results and diagnostic reports for the AI pipeline."
        operatorQuestion="Where is the technical evidence that explains current behavior?"
        badges={[
          { label: `${artifacts.data.length} artifacts`, variant: 'default' },
          { label: `${artifacts.data.filter(a => a.status === 'ready').length} ready`, variant: 'success' },
          { label: `${artifacts.data.filter(a => a.status === 'generating').length} generating`, variant: 'default' },
        ]}
        dataSource={artifacts.meta.source}
      />

      <AiLabMetricGrid columns={4} metrics={[
        { label: 'Total Artifacts', value: artifacts.data.length, icon: Archive, status: 'neutral' },
        { label: 'Benchmarks', value: artifacts.data.filter(a => a.type === 'benchmark').length, icon: FlaskConical, status: 'neutral' },
        { label: 'Eval Reports', value: artifacts.data.filter(a => a.type === 'eval').length, icon: Eye, status: 'neutral' },
        { label: 'Diagnostics', value: artifacts.data.filter(a => a.type === 'ocr_diagnostic' || a.type === 'embedding_experiment').length, icon: Cpu, status: 'neutral' },
      ]} />

      {/* Diagnostics */}
      <GlassCard className="mb-6" delay={0.1}>
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Processing Diagnostics</h3>
          <DataSourceBadge source="mock" />
        </div>
        <div className="space-y-2">
          {diagnostics.map((d, i) => (
            <motion.div key={d.label} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.03 }}
              className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors">
              <div>
                <p className="text-xs font-medium text-foreground">{d.label}</p>
                <p className="text-[10px] text-muted-foreground">{d.detail}</p>
              </div>
              <span className={`text-[10px] font-medium ${
                d.health === 'healthy' ? 'text-glow-success' : d.health === 'warning' ? 'text-glow-warning' : 'text-muted-foreground'
              }`}>{d.status}</span>
            </motion.div>
          ))}
        </div>
      </GlassCard>

      {/* Artifact Explorer */}
      <GlassCard delay={0.2}>
        <ArtifactExplorerPanel artifacts={artifacts.data} dataSource={artifacts.meta.source} />
      </GlassCard>
    </motion.div>
  );
}
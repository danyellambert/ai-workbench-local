import { motion } from 'framer-motion';
import { FileText, Upload, Search, Grid, List, AlertTriangle, Check, Loader2, Clock, Database, Layers } from 'lucide-react';
import { PageHeader, StatusPill, GlassCard, MetricCard } from '@/components/shared/ui-components';
import { documents, systemStats } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useState } from 'react';

const stagger = { animate: { transition: { staggerChildren: 0.04 } } };
const item = { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0, transition: { duration: 0.35 } } };

const pipelineSteps = [
  { label: 'Extraction', icon: FileText },
  { label: 'Chunking', icon: Layers },
  { label: 'Embeddings', icon: Database },
  { label: 'Index Sync', icon: Check },
];

export default function DocumentsPage() {
  const [view, setView] = useState<'table' | 'grid'>('table');
  const [search, setSearch] = useState('');
  const filtered = documents.filter(d => d.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" variants={stagger} initial="initial" animate="animate">
      <PageHeader title="Document Library" description="Ingest, index and manage your document corpus for AI-powered analysis.">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs">
          <Upload className="w-3.5 h-3.5 mr-2" /> Upload Documents
        </Button>
      </PageHeader>

      {/* Stats */}
      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Total Documents" value={systemStats.totalDocuments} icon={FileText} glowColor="primary" />
        <MetricCard label="Indexed" value={systemStats.indexedDocuments} icon={Check} glowColor="success" />
        <MetricCard label="Total Chunks" value={systemStats.totalChunks.toLocaleString()} icon={Layers} glowColor="accent" />
        <MetricCard label="Characters" value={(systemStats.totalChars / 1000).toFixed(0) + 'K'} icon={Database} glowColor="warning" />
      </motion.div>

      {/* Pipeline Visualization */}
      <motion.div variants={item}>
        <GlassCard className="mb-6">
          <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-4">Ingestion Pipeline</h3>
          <div className="flex items-center gap-2">
            {pipelineSteps.map((step, i) => (
              <div key={step.label} className="flex items-center gap-2 flex-1">
                <div className="flex items-center gap-2 flex-1">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <step.icon className="w-4 h-4 text-primary" />
                  </div>
                  <span className="text-xs text-foreground">{step.label}</span>
                </div>
                {i < pipelineSteps.length - 1 && (
                  <div className="w-8 h-px bg-gradient-to-r from-primary/40 to-primary/10" />
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      </motion.div>

      {/* Upload Zone */}
      <motion.div variants={item}>
        <div className="border-2 border-dashed border-border/60 rounded-xl p-8 mb-6 text-center hover:border-primary/40 transition-colors group cursor-pointer">
          <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-3 group-hover:text-primary transition-colors" />
          <p className="text-sm text-foreground mb-1">Drop files here or click to browse</p>
          <p className="text-xs text-muted-foreground">PDF, DOCX, XLSX, TXT — up to 50MB per file</p>
        </div>
      </motion.div>

      {/* Controls */}
      <motion.div variants={item} className="flex items-center justify-between mb-4 gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input placeholder="Search documents..." value={search} onChange={e => setSearch(e.target.value)}
            className="pl-9 h-8 text-xs bg-secondary/30 border-border/50" />
        </div>
        <div className="flex items-center gap-1 bg-secondary/30 rounded-lg p-0.5">
          <button onClick={() => setView('table')} className={`p-1.5 rounded-md transition-colors ${view === 'table' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
            <List className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setView('grid')} className={`p-1.5 rounded-md transition-colors ${view === 'grid' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
            <Grid className="w-3.5 h-3.5" />
          </button>
        </div>
      </motion.div>

      {/* Document Table */}
      {view === 'table' ? (
        <motion.div variants={item} className="glass rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50">
                {['Document', 'Type', 'Status', 'Chunks', 'Characters', 'Loader', 'Indexed'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc, i) => (
                <motion.tr key={doc.id}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                  className="border-b border-border/30 hover:bg-secondary/20 transition-colors cursor-pointer group">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                      <span className="text-xs text-foreground group-hover:text-primary transition-colors truncate max-w-[240px]">{doc.name}</span>
                      {doc.warnings && <AlertTriangle className="w-3 h-3 text-glow-warning shrink-0" />}
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">{doc.type}</span></td>
                  <td className="px-4 py-3"><StatusPill status={doc.status} /></td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{doc.chunks || '—'}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{doc.chars ? doc.chars.toLocaleString() : '—'}</td>
                  <td className="px-4 py-3"><span className="text-[10px] font-mono text-muted-foreground">{doc.loaderStrategy}</span></td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{doc.indexedAt ? new Date(doc.indexedAt).toLocaleDateString() : '—'}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      ) : (
        <motion.div variants={item} className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((doc, i) => (
            <motion.div key={doc.id} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.04 }}
              className="glass rounded-xl p-4 cursor-pointer hover:border-primary/30 transition-all duration-300 group">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-muted-foreground" />
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">{doc.type}</span>
                </div>
                <StatusPill status={doc.status} />
              </div>
              <h4 className="text-xs font-medium text-foreground mb-2 group-hover:text-primary transition-colors truncate">{doc.name}</h4>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <span>{doc.chunks} chunks</span>
                <span>{doc.size}</span>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

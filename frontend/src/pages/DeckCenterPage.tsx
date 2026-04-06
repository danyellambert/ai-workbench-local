import { motion } from 'framer-motion';
import { FileOutput, Download, Eye, Clock, Sparkles, FileText, Loader2 } from 'lucide-react';
import { PageHeader, StatusPill, GlassCard } from '@/components/shared/ui-components';
import { artifacts } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';

const pipelineSteps = ['Generating Contract', 'Calling Renderer', 'Building Slides', 'Ready for Download'];

export default function DeckCenterPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Deck Center" description="Executive artifact generation, export pipeline and download center.">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"><Sparkles className="w-3.5 h-3.5 mr-2" /> New Deck</Button>
      </PageHeader>

      {/* Pipeline */}
      <GlassCard className="mb-6">
        <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-4">Export Pipeline</h3>
        <div className="flex items-center gap-2">
          {pipelineSteps.map((step, i) => (
            <div key={step} className="flex items-center gap-2 flex-1">
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs flex-1 ${
                i < 3 ? 'bg-glow-success/5 text-glow-success' : i === 3 ? 'bg-primary/10 text-primary' : 'text-muted-foreground'
              }`}>
                {i < 3 ? <span className="w-4 h-4">✓</span> : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span className="hidden md:inline">{step}</span>
              </div>
              {i < pipelineSteps.length - 1 && <div className={`w-6 h-px ${i < 3 ? 'bg-glow-success/30' : 'bg-border'}`} />}
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Artifacts Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {artifacts.map((a, i) => (
          <motion.div key={a.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + i * 0.05 }}
            className="glass rounded-xl p-5 hover:border-primary/20 transition-all duration-300 group cursor-pointer">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-glow-warning/10 flex items-center justify-center">
                <FileOutput className="w-5 h-5 text-glow-warning" />
              </div>
              <StatusPill status={a.status} />
            </div>
            <h4 className="text-sm font-medium text-foreground mb-1 group-hover:text-primary transition-colors">{a.name}</h4>
            <div className="flex items-center gap-3 text-[10px] text-muted-foreground mb-3">
              <span className="uppercase">{a.type}</span>
              <span>{a.size}</span>
              <span>{a.workflow}</span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground mb-4">
              <Clock className="w-3 h-3" />
              {new Date(a.createdAt).toLocaleString()}
            </div>
            {a.status === 'ready' && (
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" className="h-7 text-[10px] flex-1 border-border/50"><Download className="w-3 h-3 mr-1" /> Download</Button>
                <Button variant="ghost" size="sm" className="h-7 text-[10px] border-border/50"><Eye className="w-3 h-3" /></Button>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Recent Export History */}
      <GlassCard className="mt-6" delay={0.4}>
        <h3 className="text-sm font-medium text-foreground mb-4">Export History</h3>
        <div className="space-y-2">
          {artifacts.filter(a => a.status === 'ready').map(a => (
            <div key={a.id} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-secondary/20 transition-colors">
              <div className="flex items-center gap-3 min-w-0">
                <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-foreground truncate">{a.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground uppercase">{a.type}</span>
              </div>
              <span className="text-[10px] text-muted-foreground shrink-0 ml-2">{new Date(a.createdAt).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </motion.div>
  );
}

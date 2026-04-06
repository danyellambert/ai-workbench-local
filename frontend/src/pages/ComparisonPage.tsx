import { motion } from 'framer-motion';
import { GitCompare, ArrowRight, Sparkles, AlertTriangle, Play, ArrowLeftRight } from 'lucide-react';
import { PageHeader, SeverityBadge, GlassCard } from '@/components/shared/ui-components';
import { comparisonDiffs, documents } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const impactColors = {
  breaking: 'bg-glow-error/10 text-glow-error border-glow-error/20',
  significant: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
  minor: 'bg-muted text-muted-foreground border-border',
};

export default function ComparisonPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Policy & Contract Comparison" description="Compare documents side-by-side with impact analysis and grounded recommendations.">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"><Play className="w-3.5 h-3.5 mr-2" /> Run Comparison</Button>
        <Button variant="outline" className="h-9 px-4 text-xs border-border/50"><Sparkles className="w-3.5 h-3.5 mr-2" /> Generate Deck</Button>
      </PageHeader>

      {/* Document Selection */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="glass rounded-xl p-5 mb-6">
        <div className="grid md:grid-cols-2 gap-4 items-end">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Document A</label>
            <Select defaultValue="d1">
              <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
              <SelectContent>{documents.filter(d => d.status === 'indexed').map(d => (<SelectItem key={d.id} value={d.id} className="text-xs">{d.name}</SelectItem>))}</SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Document B</label>
            <Select defaultValue="d4">
              <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
              <SelectContent>{documents.filter(d => d.status === 'indexed').map(d => (<SelectItem key={d.id} value={d.id} className="text-xs">{d.name}</SelectItem>))}</SelectContent>
            </Select>
          </div>
        </div>
      </motion.div>

      {/* Executive Summary */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <GlassCard className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Executive Summary</h3>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed mb-4">
            Analysis of 5 clause differences between <span className="text-foreground">MSA v4.2</span> and <span className="text-foreground">Cloud Infrastructure SLA</span> reveals
            <span className="text-glow-error font-medium"> 2 breaking</span> and
            <span className="text-glow-warning font-medium"> 2 significant</span> differences requiring immediate attention.
          </p>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-glow-error/20 border border-glow-error/30" />
              <span className="text-muted-foreground">2 Breaking</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-glow-warning/20 border border-glow-warning/30" />
              <span className="text-muted-foreground">2 Significant</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-muted border border-border" />
              <span className="text-muted-foreground">1 Minor</span>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {/* Comparison Diffs */}
      <div className="space-y-3">
        {comparisonDiffs.map((diff, i) => (
          <motion.div key={diff.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.06 }}
            className="glass rounded-xl p-5 hover:border-primary/20 transition-all duration-300">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-medium text-foreground">{diff.clause}</h4>
                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium capitalize ${impactColors[diff.impact]}`}>{diff.impact}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground">{diff.category}</span>
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4 mb-3">
              <div className="bg-glow-error/5 border border-glow-error/10 rounded-lg p-3">
                <span className="text-[10px] uppercase tracking-wider text-glow-error/60 font-medium block mb-1">Document A</span>
                <p className="text-xs text-foreground/80 leading-relaxed">{diff.docA}</p>
              </div>
              <div className="bg-glow-success/5 border border-glow-success/10 rounded-lg p-3">
                <span className="text-[10px] uppercase tracking-wider text-glow-success/60 font-medium block mb-1">Document B</span>
                <p className="text-xs text-foreground/80 leading-relaxed">{diff.docB}</p>
              </div>
            </div>
            <div className="flex items-start gap-2 bg-secondary/20 rounded-lg p-3">
              <ArrowLeftRight className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
              <p className="text-xs text-muted-foreground leading-relaxed">{diff.businessImpact}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Recommendation */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
        className="mt-6">
        <GlassCard>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Recommendation</h3>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Proceed with Document B's terms as baseline. The liability cap and IP ownership clauses in Document A present unacceptable risk.
            Negotiate Document A's data residency and incident response terms into Document B's framework. Generate a decision deck for stakeholder review.
          </p>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}

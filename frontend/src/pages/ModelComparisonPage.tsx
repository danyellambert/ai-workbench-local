import { motion } from 'framer-motion';
import { BarChart3, Trophy, Zap, Timer, FileText, CheckCircle2, Target } from 'lucide-react';
import { PageHeader, GlassCard, MetricCard } from '@/components/shared/ui-components';
import { models } from '@/lib/mock-data';
import { Progress } from '@/components/ui/progress';

export default function ModelComparisonPage() {
  const best = models.reduce((a, b) => a.useCaseFit > b.useCaseFit ? a : b);

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Model Comparison" description="Benchmark and compare models across latency, quality, adherence and groundedness." />

      {/* Leaderboard */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="glass rounded-xl p-5 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Trophy className="w-4 h-4 text-glow-warning" />
          <h3 className="text-sm font-medium text-foreground">Leaderboard</h3>
        </div>
        <div className="space-y-2">
          {[...models].sort((a, b) => b.useCaseFit - a.useCaseFit).map((model, i) => (
            <motion.div key={model.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 + i * 0.04 }}
              className={`flex items-center gap-4 py-2.5 px-3 rounded-lg transition-colors ${
                i === 0 ? 'bg-glow-warning/5 border border-glow-warning/20' : 'hover:bg-secondary/20'
              }`}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                i === 0 ? 'bg-glow-warning/20 text-glow-warning' : 'bg-secondary text-muted-foreground'
              }`}>{i + 1}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground">{model.model}</p>
                <p className="text-[10px] text-muted-foreground">{model.provider} · {model.family} · {model.quantization}</p>
              </div>
              <div className="flex items-center gap-4 text-[10px] text-muted-foreground shrink-0">
                <span><Timer className="w-3 h-3 inline mr-1" />{model.latency}s</span>
                <span><Target className="w-3 h-3 inline mr-1" />{(model.adherence * 100).toFixed(0)}%</span>
                <span className="text-xs font-semibold text-primary">{(model.useCaseFit * 100).toFixed(0)}%</span>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Comparison Cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {models.map((model, i) => (
          <motion.div key={model.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 + i * 0.06 }}
            className={`glass rounded-xl p-5 ${model.id === best.id ? 'border-primary/30' : ''}`}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="text-sm font-medium text-foreground">{model.family}</h4>
                <p className="text-[10px] text-muted-foreground font-mono">{model.model}</p>
              </div>
              {model.id === best.id && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-warning/10 text-glow-warning border border-glow-warning/20 font-medium">Best Fit</span>
              )}
            </div>

            <div className="space-y-3 mt-4">
              {[
                { label: 'Use Case Fit', value: model.useCaseFit },
                { label: 'Groundedness', value: model.groundedness },
                { label: 'Adherence', value: model.adherence },
              ].map(metric => (
                <div key={metric.label}>
                  <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
                    <span>{metric.label}</span>
                    <span className="text-foreground font-medium">{(metric.value * 100).toFixed(0)}%</span>
                  </div>
                  <Progress value={metric.value * 100} className="h-1.5 bg-secondary" />
                </div>
              ))}
            </div>

            <div className="mt-4 pt-3 border-t border-border/30 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
              <div><span className="block text-muted-foreground/60">Latency</span>{model.latency}s</div>
              <div><span className="block text-muted-foreground/60">Output</span>{model.outputChars} chars</div>
              <div><span className="block text-muted-foreground/60">Runtime</span>{model.runtimeBucket.replace('_', ' ')}</div>
              <div><span className="block text-muted-foreground/60">Quantization</span>{model.quantization}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Summary */}
      <GlassCard className="mt-6" delay={0.5}>
        <div className="flex items-center gap-2 mb-3">
          <CheckCircle2 className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Benchmark Summary</h3>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          <span className="text-foreground font-medium">{best.model}</span> achieves the highest use-case fit score ({(best.useCaseFit * 100).toFixed(0)}%)
          with strong groundedness ({(best.groundedness * 100).toFixed(0)}%) and format adherence ({(best.adherence * 100).toFixed(0)}%).
          For latency-critical applications, <span className="text-foreground">mistral:7b-instruct</span> offers 2.1s response time but with reduced quality.
          Cloud API options (GPT-4o) provide the best overall quality at the cost of external dependency.
        </p>
      </GlassCard>
    </motion.div>
  );
}

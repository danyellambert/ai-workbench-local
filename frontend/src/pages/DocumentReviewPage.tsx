import { motion } from 'framer-motion';
import { Shield, FileText, Play, Sparkles, ArrowRight, AlertTriangle, CheckCircle2, Info, ExternalLink } from 'lucide-react';
import { PageHeader, StatusPill, SeverityBadge, GlassCard } from '@/components/shared/ui-components';
import { findings, documents } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const steps = ['Select', 'Ground', 'Analyze', 'Review', 'Export'];
const currentStep = 3;

export default function DocumentReviewPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Document Review" description="Review documents for risks, gaps and findings with grounded evidence.">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs">
          <Play className="w-3.5 h-3.5 mr-2" /> Run Review
        </Button>
        <Button variant="outline" className="h-9 px-4 text-xs border-border/50">
          <Sparkles className="w-3.5 h-3.5 mr-2" /> Generate Deck
        </Button>
      </PageHeader>

      {/* Stepper */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="glass rounded-xl p-4 mb-6">
        <div className="flex items-center gap-1">
          {steps.map((step, i) => (
            <div key={step} className="flex items-center gap-1 flex-1">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                i < currentStep ? 'text-glow-success' : i === currentStep ? 'text-primary bg-primary/10' : 'text-muted-foreground'
              }`}>
                {i < currentStep ? <CheckCircle2 className="w-3.5 h-3.5" /> : <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">{i + 1}</span>}
                <span className="hidden sm:inline">{step}</span>
              </div>
              {i < steps.length - 1 && <div className={`flex-1 h-px ${i < currentStep ? 'bg-glow-success/40' : 'bg-border'}`} />}
            </div>
          ))}
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-12 gap-4">
        {/* Left Panel */}
        <div className="lg:col-span-4 space-y-4">
          <GlassCard delay={0.15}>
            <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Document Selection</h3>
            <Select defaultValue="d1">
              <SelectTrigger className="h-8 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
              <SelectContent>
                {documents.filter(d => d.status === 'indexed').map(d => (
                  <SelectItem key={d.id} value={d.id} className="text-xs">{d.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="mt-3 space-y-1.5">
              <div className="flex justify-between text-[10px] text-muted-foreground"><span>Chunks</span><span>347</span></div>
              <div className="flex justify-between text-[10px] text-muted-foreground"><span>Characters</span><span>189,420</span></div>
              <div className="flex justify-between text-[10px] text-muted-foreground"><span>Strategy</span><span className="font-mono">document_scan</span></div>
            </div>
          </GlassCard>

          <GlassCard delay={0.2}>
            <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Grounding Preview</h3>
            <div className="bg-secondary/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-1.5 h-1.5 rounded-full bg-glow-success" />
                <span className="text-[10px] text-glow-success font-medium">Context loaded</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">
                Section 7.3 establishes the liability framework under which both parties operate. The current language specifies unlimited liability exposure for material breaches, with no cap or limitation period...
              </p>
            </div>
          </GlassCard>

          <GlassCard delay={0.25}>
            <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Decision Summary</h3>
            <div className="bg-glow-warning/5 border border-glow-warning/20 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-3.5 h-3.5 text-glow-warning" />
                <span className="text-xs font-medium text-glow-warning">Requires Attention</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                2 critical and 2 high-severity findings identified. Liability and compliance clauses require immediate legal review before contract execution.
              </p>
            </div>
          </GlassCard>
        </div>

        {/* Right Panel — Findings */}
        <div className="lg:col-span-8">
          <Tabs defaultValue="findings" className="w-full">
            <TabsList className="bg-secondary/30 border border-border/50 mb-4">
              <TabsTrigger value="findings" className="text-xs data-[state=active]:bg-secondary">Findings ({findings.length})</TabsTrigger>
              <TabsTrigger value="evidence" className="text-xs data-[state=active]:bg-secondary">Evidence</TabsTrigger>
              <TabsTrigger value="artifacts" className="text-xs data-[state=active]:bg-secondary">Artifacts</TabsTrigger>
            </TabsList>

            <TabsContent value="findings" className="space-y-3 mt-0">
              {findings.map((f, i) => (
                <motion.div key={f.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.05 }}
                  className="glass rounded-xl p-4 hover:border-primary/20 transition-all duration-300 cursor-pointer group">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={f.severity} />
                      <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground">{f.category}</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">Confidence: {(f.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <h4 className="text-sm font-medium text-foreground mb-1 group-hover:text-primary transition-colors">{f.title}</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed mb-3">{f.description}</p>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1 text-[10px] text-muted-foreground bg-secondary/40 px-2 py-1 rounded">
                        <FileText className="w-3 h-3" />
                        <span className="truncate max-w-[150px]">{f.source}</span>
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground/60">{f.chunkId}</span>
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div className="mt-3 pt-3 border-t border-border/30">
                    <div className="flex items-start gap-2">
                      <Info className="w-3 h-3 text-primary mt-0.5 shrink-0" />
                      <p className="text-[11px] text-primary/80">{f.recommendation}</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </TabsContent>

            <TabsContent value="evidence" className="mt-0">
              <GlassCard>
                <h3 className="text-sm font-medium text-foreground mb-3">Evidence Trail</h3>
                {findings.slice(0, 3).map(f => (
                  <div key={f.id} className="py-3 border-b border-border/30 last:border-0">
                    <div className="flex items-center gap-2 mb-2">
                      <SeverityBadge severity={f.severity} />
                      <span className="text-xs text-foreground">{f.title}</span>
                    </div>
                    <div className="bg-secondary/30 rounded-lg p-3 text-xs text-muted-foreground font-mono leading-relaxed">
                      <span className="text-primary">[{f.chunkId}]</span> {f.description.slice(0, 120)}...
                    </div>
                  </div>
                ))}
              </GlassCard>
            </TabsContent>

            <TabsContent value="artifacts" className="mt-0">
              <GlassCard>
                <h3 className="text-sm font-medium text-foreground mb-3">Generated Artifacts</h3>
                <div className="space-y-2">
                  {['review_deck.pptx', 'review.json', 'contract_payload.json'].map(name => (
                    <div key={name} className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors">
                      <div className="flex items-center gap-2">
                        <StatusPill status="ready" />
                        <span className="text-xs text-foreground">{name}</span>
                      </div>
                      <Button variant="ghost" size="sm" className="h-7 text-[10px] text-muted-foreground hover:text-foreground">Download</Button>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </motion.div>
  );
}

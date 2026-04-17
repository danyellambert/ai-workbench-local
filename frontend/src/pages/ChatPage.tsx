import { motion } from 'framer-motion';
import { useState } from 'react';
import { MessageSquare, Send, FileText, Sparkles, Activity, Database, Clock, Gauge } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { GlassCard } from '@/components/shared/ui-components';
import { chatMessages, documents } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAppStore } from '@/lib/store';

export default function ChatPage() {
  const [input, setInput] = useState('');
  const operatorPreferences = useAppStore((state) => state.operatorPreferences);

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto h-[calc(100vh-3.5rem)] flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Document / Chat Experiments"
        description="Diagnostic RAG surface for document interaction, retrieval quality assessment and grounding validation."
        operatorQuestion="Is RAG helping or just adding noise and cost?"
        badges={[
          { label: 'Experimental', variant: 'default' },
          { label: 'hybrid_rerank', variant: 'default' },
          { label: 'top-k: 15', variant: 'default' },
        ]}
        dataSource="mock"
      />

      <div className="flex-1 flex gap-4 min-h-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
            {chatMessages.map((msg, i) => (
              <motion.div key={msg.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-xl p-4 ${
                  msg.role === 'user' ? 'bg-primary/10 border border-primary/20' : 'glass'
                }`}>
                  <p className="text-xs text-foreground leading-relaxed whitespace-pre-line">{msg.content}</p>
                  {msg.role === 'assistant' && operatorPreferences.defaultEvidencePanelOpen && 'sources' in msg && msg.sources && (
                    <div className="mt-3 pt-3 border-t border-border/30">
                      <p className="text-[9px] text-muted-foreground/50 uppercase tracking-wider mb-1.5">Grounding Sources</p>
                      <div className="flex items-center gap-2 flex-wrap">
                        {msg.sources.map((src: any, j: number) => (
                          <span key={j} className="text-[10px] px-2 py-1 rounded-md bg-secondary/50 text-muted-foreground flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors">
                            <FileText className="w-3 h-3" />{src.doc} · {src.chunk}
                            {operatorPreferences.showSourceBadges ? <span className="text-primary/60">{(src.score * 100).toFixed(0)}%</span> : null}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Suggested prompts */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            {['What are the key risks in the Master Service Agreement v4.2?', 'Summarize the Cloud Infrastructure SLA terms', 'Compare liability clauses across MSA and Data Processing Addendum'].map(p => (
              <button key={p} onClick={() => setInput(p)}
                className="text-[10px] px-3 py-1.5 rounded-lg bg-secondary/30 border border-border/50 text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors">
                <Sparkles className="w-3 h-3 inline mr-1" />{p}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="flex items-center gap-2 glass rounded-xl p-2">
            <Input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask about your documents..."
              className="border-0 bg-transparent text-xs focus-visible:ring-0 h-8" />
            <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90 h-8 w-8 p-0 shrink-0">
              <Send className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Right Panel */}
        <div className="hidden lg:block w-72 space-y-4">
          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Selected Documents</h4>
              <DataSourceBadge source="mock" />
            </div>
            <div className="space-y-2">
              {documents.filter(d => d.status === 'indexed').slice(0, 4).map(d => (
                <div key={d.id} className="flex items-center gap-2 text-xs text-muted-foreground py-1">
                  <FileText className="w-3 h-3 shrink-0" />
                  <span className="truncate">{d.name}</span>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Session Diagnostics</h4>
              <DataSourceBadge source="mock" />
            </div>
            <div className="space-y-2 text-[10px] text-muted-foreground">
              {[
                { icon: MessageSquare, label: 'Messages', value: '4' },
                { icon: Database, label: 'Tokens used', value: '2,847' },
                { icon: Clock, label: 'Avg latency', value: '3.2s' },
                { icon: Activity, label: 'Model', value: 'qwen2.5:32b' },
                { icon: Gauge, label: 'Top-K', value: '15' },
                { icon: Gauge, label: 'Context used', value: '18,420 / 32,768' },
              ].map(s => (
                <div key={s.label} className="flex justify-between items-center">
                  <div className="flex items-center gap-1.5">
                    <s.icon className="w-3 h-3" />
                    <span>{s.label}</span>
                  </div>
                  <span className="text-foreground font-mono">{s.value}</span>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Retrieval Quality</h4>
            <div className="space-y-2 text-[10px] text-muted-foreground">
              <div className="flex justify-between"><span>Strategy</span><span className="text-foreground font-mono">hybrid_rerank</span></div>
              <div className="flex justify-between"><span>Rerank pool</span><span className="text-foreground">50</span></div>
              <div className="flex justify-between"><span>Avg relevance</span><span className="text-foreground">87%</span></div>
              <div className="flex justify-between"><span>Chunks retrieved</span><span className="text-foreground">15</span></div>
            </div>
          </GlassCard>
        </div>
      </div>
    </motion.div>
  );
}
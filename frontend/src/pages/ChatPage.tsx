import { motion } from 'framer-motion';
import { useState } from 'react';
import { MessageSquare, Send, FileText, Info, ChevronRight, Sparkles, Zap } from 'lucide-react';
import { PageHeader, GlassCard } from '@/components/shared/ui-components';
import { chatMessages, documents } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function ChatPage() {
  const [input, setInput] = useState('');

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto h-[calc(100vh-3.5rem)] flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Chat with RAG" description="Conversational AI grounded in your indexed documents." />

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
                  {msg.role === 'assistant' && 'sources' in msg && msg.sources && (
                    <div className="mt-3 pt-3 border-t border-border/30 flex items-center gap-2 flex-wrap">
                      {msg.sources.map((src: any, j: number) => (
                        <span key={j} className="text-[10px] px-2 py-1 rounded-md bg-secondary/50 text-muted-foreground flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors">
                          <FileText className="w-3 h-3" />{src.doc} · {src.chunk}
                          <span className="text-primary/60">{(src.score * 100).toFixed(0)}%</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Suggested prompts */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            {['What are the key risks?', 'Summarize the SLA terms', 'Compare liability clauses'].map(p => (
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

        {/* Right Sidebar */}
        <div className="hidden lg:block w-72 space-y-4">
          <GlassCard>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Selected Documents</h4>
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
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Session Stats</h4>
            <div className="space-y-2 text-[10px] text-muted-foreground">
              <div className="flex justify-between"><span>Messages</span><span className="text-foreground">4</span></div>
              <div className="flex justify-between"><span>Tokens used</span><span className="text-foreground">2,847</span></div>
              <div className="flex justify-between"><span>Avg latency</span><span className="text-foreground">3.2s</span></div>
              <div className="flex justify-between"><span>Model</span><span className="text-foreground font-mono">qwen2.5:32b</span></div>
              <div className="flex justify-between"><span>Top-K</span><span className="text-foreground">15</span></div>
            </div>
          </GlassCard>
        </div>
      </div>
    </motion.div>
  );
}

import { motion } from 'framer-motion';
import { Layers, Play, FileText, Code, CheckSquare, Bot, User, Sparkles } from 'lucide-react';
import { PageHeader, GlassCard } from '@/components/shared/ui-components';
import { structuredTasks, documents } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useState } from 'react';

const iconMap: Record<string, React.ElementType> = { Layers, FileText, CheckSquare: CheckSquare, Bot, User, Code };

const sampleOutput = {
  task: "extraction",
  document: "Master Service Agreement v4.2",
  entities: [
    { type: "Organization", value: "Acme Corp", confidence: 0.96 },
    { type: "Date", value: "2024-01-15", confidence: 0.99 },
    { type: "Amount", value: "$2,400,000 annually", confidence: 0.94 },
    { type: "Duration", value: "36 months", confidence: 0.97 },
    { type: "Jurisdiction", value: "State of Delaware", confidence: 0.92 },
  ]
};

export default function StructuredOutputsPage() {
  const [selectedTask, setSelectedTask] = useState('extraction');

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Structured Outputs" description="Execute structured AI tasks on indexed documents with schema-validated results." />

      <div className="grid lg:grid-cols-12 gap-4">
        {/* Left - Controls */}
        <div className="lg:col-span-4 space-y-4">
          <GlassCard>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Task Selection</h4>
            <div className="space-y-1.5">
              {structuredTasks.map(task => {
                const Icon = iconMap[task.icon] || Layers;
                return (
                  <button key={task.id} onClick={() => setSelectedTask(task.name)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                      selectedTask === task.name ? 'bg-primary/10 text-primary border border-primary/20' : 'hover:bg-secondary/30 text-muted-foreground'
                    }`}>
                    <Icon className="w-4 h-4 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs font-medium">{task.label}</p>
                      <p className="text-[10px] text-muted-foreground/70 truncate">{task.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </GlassCard>

          <GlassCard>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Document</h4>
            <Select defaultValue="d1">
              <SelectTrigger className="h-8 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
              <SelectContent>{documents.filter(d => d.status === 'indexed').map(d => (
                <SelectItem key={d.id} value={d.id} className="text-xs">{d.name}</SelectItem>
              ))}</SelectContent>
            </Select>
          </GlassCard>

          <GlassCard>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Instructions</h4>
            <Textarea placeholder="Optional additional instructions..." className="text-xs bg-secondary/30 border-border/50 min-h-[80px]" />
          </GlassCard>

          <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90 h-9 text-xs">
            <Play className="w-3.5 h-3.5 mr-2" /> Run Task
          </Button>
        </div>

        {/* Right - Output */}
        <div className="lg:col-span-8">
          <Tabs defaultValue="visual">
            <TabsList className="bg-secondary/30 border border-border/50 mb-4">
              <TabsTrigger value="visual" className="text-xs data-[state=active]:bg-secondary">Visual</TabsTrigger>
              <TabsTrigger value="json" className="text-xs data-[state=active]:bg-secondary">JSON</TabsTrigger>
              <TabsTrigger value="table" className="text-xs data-[state=active]:bg-secondary">Table</TabsTrigger>
            </TabsList>

            <TabsContent value="visual" className="mt-0">
              <GlassCard>
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-medium text-foreground">Extraction Results</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-success/10 text-glow-success border border-glow-success/20">5 entities</span>
                </div>
                <div className="space-y-2">
                  {sampleOutput.entities.map((entity, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.2 + i * 0.05 }}
                      className="flex items-center justify-between py-2.5 px-3 rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors">
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary font-medium">{entity.type}</span>
                        <span className="text-xs text-foreground">{entity.value}</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground">{(entity.confidence * 100).toFixed(0)}%</span>
                    </motion.div>
                  ))}
                </div>
              </GlassCard>
            </TabsContent>

            <TabsContent value="json" className="mt-0">
              <GlassCard>
                <pre className="text-xs text-foreground/80 font-mono leading-relaxed overflow-auto max-h-[500px]">
                  {JSON.stringify(sampleOutput, null, 2)}
                </pre>
              </GlassCard>
            </TabsContent>

            <TabsContent value="table" className="mt-0">
              <div className="glass rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border/50">
                      {['Type', 'Value', 'Confidence'].map(h => (
                        <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sampleOutput.entities.map((entity, i) => (
                      <tr key={i} className="border-b border-border/30 hover:bg-secondary/20 transition-colors">
                        <td className="px-4 py-3"><span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary">{entity.type}</span></td>
                        <td className="px-4 py-3 text-xs text-foreground">{entity.value}</td>
                        <td className="px-4 py-3 text-xs text-muted-foreground">{(entity.confidence * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </motion.div>
  );
}

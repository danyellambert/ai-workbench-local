import { motion } from 'framer-motion';
import { Settings, Server, Palette } from 'lucide-react';
import { PageHeader, GlassCard } from '@/components/shared/ui-components';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';

export default function SettingsPage() {
  const Control = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );

  return (
    <motion.div className="p-6 lg:p-8 max-w-[900px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Runtime Controls" description="Configure generation, retrieval and document processing settings." />

      <div className="space-y-6">
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Generation</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Control label="Provider">
              <Select defaultValue="ollama"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="ollama">Ollama</SelectItem><SelectItem value="openai">OpenAI Compatible</SelectItem><SelectItem value="hf">HuggingFace Server</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Model">
              <Select defaultValue="qwen"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="qwen">qwen2.5:32b-instruct-q5_K_M</SelectItem><SelectItem value="llama">llama3.1:70b-instruct-q4_K_M</SelectItem><SelectItem value="mistral">mistral:7b-instruct-v0.3</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Temperature — 0.3">
              <Slider defaultValue={[0.3]} min={0} max={1} step={0.05} className="py-2" />
            </Control>
            <Control label="Context Window">
              <Select defaultValue="auto"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="auto">Auto</SelectItem><SelectItem value="4k">4,096</SelectItem><SelectItem value="8k">8,192</SelectItem><SelectItem value="16k">16,384</SelectItem><SelectItem value="32k">32,768</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Prompt Profile">
              <Select defaultValue="balanced"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="balanced">Balanced</SelectItem><SelectItem value="precise">Precise</SelectItem><SelectItem value="creative">Creative</SelectItem></SelectContent>
              </Select>
            </Control>
          </div>
        </GlassCard>

        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <Settings className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-medium text-foreground">Retrieval</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Control label="Embedding Provider">
              <Select defaultValue="ollama"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="ollama">Ollama</SelectItem><SelectItem value="hf">HuggingFace</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Embedding Model">
              <Select defaultValue="nomic"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="nomic">nomic-embed-text</SelectItem><SelectItem value="bge">bge-m3</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Top-K — 15">
              <Slider defaultValue={[15]} min={3} max={50} step={1} className="py-2" />
            </Control>
            <Control label="Retrieval Strategy">
              <Select defaultValue="hybrid"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="hybrid">Hybrid (semantic + lexical)</SelectItem><SelectItem value="semantic">Semantic only</SelectItem><SelectItem value="lexical">Lexical only</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Chunk Size — 1200">
              <Slider defaultValue={[1200]} min={256} max={4096} step={64} className="py-2" />
            </Control>
            <Control label="Chunk Overlap — 200">
              <Slider defaultValue={[200]} min={0} max={512} step={32} className="py-2" />
            </Control>
            <Control label="Rerank Pool Size — 50">
              <Slider defaultValue={[50]} min={10} max={200} step={5} className="py-2" />
            </Control>
            <Control label="Rerank Lexical Weight — 0.3">
              <Slider defaultValue={[0.3]} min={0} max={1} step={0.05} className="py-2" />
            </Control>
          </div>
        </GlassCard>

        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Document Processing</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Control label="PDF Extraction Mode">
              <Select defaultValue="plumber"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="plumber">pdf_plumber</SelectItem><SelectItem value="marker">marker</SelectItem><SelectItem value="ocr">OCR fallback</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="OCR Backend">
              <Select defaultValue="tesseract"><SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="tesseract">Tesseract</SelectItem><SelectItem value="surya">Surya</SelectItem></SelectContent>
              </Select>
            </Control>
            <div className="flex items-center justify-between col-span-full">
              <div>
                <Label className="text-xs text-foreground">VLM Enhancement</Label>
                <p className="text-[10px] text-muted-foreground">Use vision-language model for complex layouts</p>
              </div>
              <Switch />
            </div>
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}

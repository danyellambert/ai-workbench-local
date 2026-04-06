import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { useAppStore } from '@/lib/store';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

export default function RuntimeDrawer() {
  const { runtimeDrawerOpen, setRuntimeDrawerOpen } = useAppStore();

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="space-y-3">
      <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{title}</h4>
      {children}
    </div>
  );

  const Control = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );

  return (
    <Sheet open={runtimeDrawerOpen} onOpenChange={setRuntimeDrawerOpen}>
      <SheetContent className="w-[380px] bg-card border-border overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm flex items-center gap-2">
            Runtime Controls
            <Badge variant="outline" className="text-[10px] border-glow-success/30 text-glow-success">Active</Badge>
          </SheetTitle>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          <Section title="Generation">
            <Control label="Provider">
              <Select defaultValue="ollama"><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="ollama">Ollama</SelectItem><SelectItem value="openai">OpenAI Compatible</SelectItem><SelectItem value="hf">HuggingFace Server</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Model">
              <Select defaultValue="qwen"><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="qwen">qwen2.5:32b-instruct</SelectItem><SelectItem value="llama">llama3.1:70b-instruct</SelectItem><SelectItem value="mistral">mistral:7b-instruct</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Temperature — 0.3">
              <Slider defaultValue={[0.3]} min={0} max={1} step={0.05} className="py-1" />
            </Control>
            <Control label="Context Window">
              <Select defaultValue="auto"><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="auto">Auto</SelectItem><SelectItem value="4k">4,096</SelectItem><SelectItem value="8k">8,192</SelectItem><SelectItem value="16k">16,384</SelectItem><SelectItem value="32k">32,768</SelectItem></SelectContent>
              </Select>
            </Control>
          </Section>

          <Separator />

          <Section title="Retrieval">
            <Control label="Embedding Model">
              <Select defaultValue="nomic"><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="nomic">nomic-embed-text</SelectItem><SelectItem value="bge">bge-m3</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="Top-K — 15">
              <Slider defaultValue={[15]} min={3} max={50} step={1} className="py-1" />
            </Control>
            <Control label="Chunk Size — 1200">
              <Slider defaultValue={[1200]} min={256} max={4096} step={64} className="py-1" />
            </Control>
            <Control label="Chunk Overlap — 200">
              <Slider defaultValue={[200]} min={0} max={512} step={32} className="py-1" />
            </Control>
            <Control label="Rerank Pool Size — 50">
              <Slider defaultValue={[50]} min={10} max={200} step={5} className="py-1" />
            </Control>
          </Section>

          <Separator />

          <Section title="Document Processing">
            <Control label="PDF Extraction">
              <Select defaultValue="plumber"><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="plumber">pdf_plumber</SelectItem><SelectItem value="marker">marker</SelectItem><SelectItem value="ocr">OCR fallback</SelectItem></SelectContent>
              </Select>
            </Control>
            <Control label="OCR Backend">
              <Select defaultValue="tesseract"><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="tesseract">Tesseract</SelectItem><SelectItem value="surya">Surya</SelectItem></SelectContent>
              </Select>
            </Control>
          </Section>
        </div>
      </SheetContent>
    </Sheet>
  );
}

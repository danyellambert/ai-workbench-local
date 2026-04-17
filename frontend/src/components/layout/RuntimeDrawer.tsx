import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useAppStore } from '@/lib/store';
import { getRuntimeControls } from '@/lib/product-api';
import {
  buildCatalogLookup,
  deriveRuntimeFallbackChain,
  formatRuntimeUpdatedAt,
  getRuntimeConnection,
} from '@/lib/runtime-controls-ui';

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="space-y-3">
    <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</h4>
    {children}
  </div>
);

const Control = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="space-y-1.5">
    <Label className="text-xs text-muted-foreground">{label}</Label>
    {children}
  </div>
);

const ValueBox = ({ children, mono = false }: { children: React.ReactNode; mono?: boolean }) => (
  <div className={`rounded-md border border-border/50 bg-secondary/20 px-3 py-2 text-xs text-foreground ${mono ? 'font-mono text-[11px]' : ''}`}>
    {children}
  </div>
);

export default function RuntimeDrawer() {
  const { runtimeDrawerOpen, setRuntimeDrawerOpen } = useAppStore();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['runtime-controls'],
    queryFn: getRuntimeControls,
    refetchOnWindowFocus: false,
  });

  const activeProfile = data?.active_profile;
  const primaryConnection = activeProfile ? getRuntimeConnection(data, activeProfile.primaryConnectionId) : undefined;
  const embeddingConnection = activeProfile ? getRuntimeConnection(data, activeProfile.embeddingConnectionId) : undefined;
  const policyLookup = buildCatalogLookup(data?.catalogs.executionPolicies);
  const docPresetLookup = buildCatalogLookup(data?.catalogs.docPresets);
  const qualityLookup = buildCatalogLookup(data?.catalogs.qualityPostures);
  const fallbackChain = activeProfile ? deriveRuntimeFallbackChain(activeProfile, data) : [];

  return (
    <Sheet open={runtimeDrawerOpen} onOpenChange={setRuntimeDrawerOpen}>
      <SheetContent className="w-[380px] overflow-y-auto border-border bg-card">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-sm">
            Runtime Controls
            <Badge variant="outline" className="border-glow-success/30 text-[10px] text-glow-success">
              Live
            </Badge>
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {!activeProfile && (
            <div className="rounded-lg border border-border/50 bg-secondary/20 p-3 text-[10px] text-muted-foreground">
              {isLoading ? 'Loading live runtime controls…' : isError ? 'Runtime Controls unavailable from backend.' : 'No runtime profile available.'}
            </div>
          )}

          {activeProfile && (
            <>
              <div className="space-y-2 rounded-lg border border-border/50 bg-secondary/20 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-xs font-medium text-foreground">{activeProfile.name}</p>
                    <p className="text-[10px] text-muted-foreground">{primaryConnection?.name ?? activeProfile.primaryConnectionId} · {activeProfile.primaryModel}</p>
                  </div>
                  <Badge variant="outline" className="border-primary/30 text-[9px] text-primary">
                    {policyLookup[activeProfile.executionPolicy]?.label ?? activeProfile.executionPolicy}
                  </Badge>
                </div>
                <p className="text-[10px] text-muted-foreground">Embedding via {embeddingConnection?.name ?? activeProfile.embeddingConnectionId} · {activeProfile.embeddingModel}</p>
                <p className="text-[10px] text-muted-foreground">Doc preset: {docPresetLookup[activeProfile.docProcessingPreset]?.label ?? activeProfile.docProcessingPreset}</p>
                <p className="text-[10px] text-muted-foreground">Quality: {qualityLookup[activeProfile.qualityPosture]?.label ?? activeProfile.qualityPosture}</p>
                <p className="text-[10px] text-muted-foreground">Updated: {formatRuntimeUpdatedAt(data?.updated_at)}</p>
                <div className="pt-1">
                  <Button asChild variant="outline" className="h-8 w-full text-xs" onClick={() => setRuntimeDrawerOpen(false)}>
                    <Link to="/app/settings/runtime">Open full Runtime Controls</Link>
                  </Button>
                </div>
              </div>

              <Section title="Generation">
                <Control label="Provider Connection">
                  <ValueBox>{primaryConnection?.name ?? activeProfile.primaryConnectionId}</ValueBox>
                </Control>
                <Control label="Model">
                  <ValueBox mono>{activeProfile.primaryModel}</ValueBox>
                </Control>
                <Control label={`Temperature — ${activeProfile.generation.temperature}`}>
                  <ValueBox>{activeProfile.generation.temperature}</ValueBox>
                </Control>
                <Control label={`Top-P — ${activeProfile.generation.topP}`}>
                  <ValueBox>{activeProfile.generation.topP}</ValueBox>
                </Control>
                <Control label={`Max Output Tokens — ${activeProfile.generation.maxOutputTokens}`}>
                  <ValueBox>{activeProfile.generation.maxOutputTokens}</ValueBox>
                </Control>
                <Control label="Context Window">
                  <ValueBox>{activeProfile.generation.contextWindow}</ValueBox>
                </Control>
                <Control label="Prompt Profile">
                  <ValueBox>{activeProfile.generation.promptProfile}</ValueBox>
                </Control>
              </Section>

              <Separator />

              <Section title="Retrieval">
                <Control label="Embedding Connection">
                  <ValueBox>{embeddingConnection?.name ?? activeProfile.embeddingConnectionId}</ValueBox>
                </Control>
                <Control label="Embedding Model">
                  <ValueBox mono>{activeProfile.embeddingModel}</ValueBox>
                </Control>
                <Control label="Retrieval Strategy">
                  <ValueBox>{activeProfile.retrievalStrategy}</ValueBox>
                </Control>
                <Control label={`Top-K — ${activeProfile.retrieval.topK}`}>
                  <ValueBox>{activeProfile.retrieval.topK}</ValueBox>
                </Control>
                <Control label={`Chunk Size — ${activeProfile.retrieval.chunkSize}`}>
                  <ValueBox>{activeProfile.retrieval.chunkSize}</ValueBox>
                </Control>
                <Control label={`Chunk Overlap — ${activeProfile.retrieval.chunkOverlap}`}>
                  <ValueBox>{activeProfile.retrieval.chunkOverlap}</ValueBox>
                </Control>
                <Control label={`Rerank Pool Size — ${activeProfile.retrieval.rerankPoolSize}`}>
                  <ValueBox>{activeProfile.retrieval.rerankPoolSize}</ValueBox>
                </Control>
              </Section>

              <Separator />

              <Section title="Document Processing">
                <Control label="PDF Extraction">
                  <ValueBox>{activeProfile.docProcessing.pdfExtractionMode}</ValueBox>
                </Control>
                <Control label="OCR Backend">
                  <ValueBox>{activeProfile.docProcessing.ocrBackend}</ValueBox>
                </Control>
                <Control label="Table Extraction">
                  <ValueBox>{activeProfile.docProcessing.tableExtractionMode}</ValueBox>
                </Control>
                <Control label={`Scanned Doc Threshold — ${activeProfile.docProcessing.scannedDocumentThreshold}`}>
                  <ValueBox>{activeProfile.docProcessing.scannedDocumentThreshold}</ValueBox>
                </Control>
              </Section>

              {fallbackChain.length > 0 && (
                <>
                  <Separator />
                  <Section title="Fallback Chain">
                    <div className="space-y-2">
                      {fallbackChain.map((step) => (
                        <ValueBox key={`${step.connectionId}-${step.model}`}>
                          {step.label} · {step.model}
                        </ValueBox>
                      ))}
                    </div>
                  </Section>
                </>
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
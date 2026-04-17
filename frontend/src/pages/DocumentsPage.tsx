import { motion } from 'framer-motion';
import { FileText, Upload, Search, Grid, List, AlertTriangle, Check, Database, Layers, AlertCircle, Loader2, FileSearch, HardDrive, ScanSearch, Trash2 } from 'lucide-react';
import { PageHeader, StatusPill, GlassCard, MetricCard } from '@/components/shared/ui-components';
import { deleteProductDocuments, getProductDocumentLibrary, getProductUploadJob, type ProductDocumentLibraryEntry, type ProductUploadDocumentsResponse, uploadProductDocuments } from '@/lib/product-api';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';

const stagger = { animate: { transition: { staggerChildren: 0.04 } } };
const item = { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0, transition: { duration: 0.35 } } };

const pipelineSteps = [
  { key: 'extraction', label: 'Extraction', icon: FileText },
  { key: 'chunking', label: 'Chunking', icon: Layers },
  { key: 'embeddings', label: 'Embeddings', icon: Database },
  { key: 'index_sync', label: 'Index Sync', icon: Check },
];

type UploadFeedbackState = { type: 'success' | 'error' | 'info'; message: string } | null;

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function buildEmptyStateMessage(isLoading: boolean, totalDocuments: number, search: string): string {
  if (isLoading) return 'Loading document library...';
  if (totalDocuments === 0) return 'No documents were found in the indexed corpus.';
  if (search.trim()) return `No documents match “${search.trim()}”.`;
  return 'No documents were found in the indexed corpus.';
}

export default function DocumentsPage() {
  const [view, setView] = useState<'table' | 'grid'>('table');
  const [search, setSearch] = useState('');
  const [selectedDocument, setSelectedDocument] = useState<ProductDocumentLibraryEntry | null>(null);
  const [dropActive, setDropActive] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<UploadFeedbackState>(null);
  const [activeUploadJobId, setActiveUploadJobId] = useState<string | null>(null);
  const [uploadJobSeed, setUploadJobSeed] = useState<ProductUploadDocumentsResponse | null>(null);
  const [documentPendingDelete, setDocumentPendingDelete] = useState<ProductDocumentLibraryEntry | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const handledUploadTerminalStateRef = useRef<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['product-document-library'],
    queryFn: getProductDocumentLibrary,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const { data: uploadJob } = useQuery({
    queryKey: ['product-upload-job', activeUploadJobId],
    queryFn: () => getProductUploadJob(activeUploadJobId || ''),
    enabled: Boolean(activeUploadJobId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchInterval: (query) => {
      const payload = query.state.data as ProductUploadDocumentsResponse | undefined;
      if (!payload) return 1000;
      return payload.status === 'completed' || payload.status === 'error' ? false : 1000;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: uploadProductDocuments,
    onMutate: () => {
      handledUploadTerminalStateRef.current = null;
      setUploadFeedback(null);
    },
    onSuccess: (payload) => {
      setActiveUploadJobId(payload.job_id);
      setUploadJobSeed(payload);
      setUploadFeedback({
        type: 'info',
        message: payload.message || 'Upload accepted. Preparing ingestion pipeline.',
      });
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    onError: (error) => {
      setUploadFeedback({
        type: 'error',
        message: error instanceof Error ? error.message : 'Document upload failed.',
      });
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProductDocuments,
    onSuccess: async (payload) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-document-library'] }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      if (selectedDocument && payload.removed_document_ids.includes(selectedDocument.document_id)) {
        setSelectedDocument(null);
      }
      setDocumentPendingDelete(null);
      setUploadFeedback({
        type: 'success',
        message: payload.message || `${payload.removed_count} document(s) removed successfully.`,
      });
    },
    onError: (error) => {
      setUploadFeedback({
        type: 'error',
        message: error instanceof Error ? error.message : 'Document deletion failed.',
      });
    },
  });

  const pipelineJob = uploadJob ?? uploadJobSeed;
  const uploadInProgress = uploadMutation.isPending || ['queued', 'running'].includes(pipelineJob?.status || '');

  useEffect(() => {
    if (!uploadJob) return;
    const terminalKey = `${uploadJob.job_id}:${uploadJob.status}`;
    if (handledUploadTerminalStateRef.current === terminalKey) return;

    if (uploadJob.status === 'completed') {
      handledUploadTerminalStateRef.current = terminalKey;
      setUploadJobSeed(uploadJob);
      setActiveUploadJobId(null);
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-document-library'] }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      const ignoredSuffix = uploadJob.ignored_count ? ` ${uploadJob.ignored_count} file(s) were ignored because they exceeded the upload limit.` : '';
      setUploadFeedback({
        type: 'success',
        message: uploadJob.message || `${uploadJob.uploaded_count} document(s) indexed successfully.${ignoredSuffix}`,
      });
      return;
    }

    if (uploadJob.status === 'error') {
      handledUploadTerminalStateRef.current = terminalKey;
      setUploadJobSeed(uploadJob);
      setActiveUploadJobId(null);
      setUploadFeedback({
        type: 'error',
        message: uploadJob.error || uploadJob.message || 'Document upload failed.',
      });
    }
  }, [queryClient, uploadJob]);

  const documents = data?.documents ?? [];
  const summary = data?.summary;
  const filtered = documents.filter(d => {
    const haystack = `${d.name} ${d.file_type || ''} ${d.loader_strategy_label || ''}`.toLowerCase();
    return haystack.includes(search.toLowerCase());
  });
  const emptyStateMessage = buildEmptyStateMessage(isLoading, documents.length, search);
  const pipelineStageLookup = new Map((pipelineJob?.steps || []).map(step => [step.key, step]));
  const pipelineStatusMessage = pipelineJob?.message || (uploadInProgress ? 'Preparing ingestion pipeline...' : 'Pipeline status will appear here during document indexing.');

  const handleOpenFilePicker = () => {
    if (uploadInProgress) return;
    fileInputRef.current?.click();
  };

  const handleFilesSelected = (fileList: FileList | File[] | null) => {
    const files = Array.from(fileList ?? []);
    if (!files.length) return;
    uploadMutation.mutate(files);
  };

  const requestDeleteDocument = (document: ProductDocumentLibraryEntry) => {
    if (deleteMutation.isPending) return;
    setDocumentPendingDelete(document);
  };

  const confirmDeleteDocument = () => {
    if (!documentPendingDelete || deleteMutation.isPending) return;
    deleteMutation.mutate([documentPendingDelete.document_id]);
  };

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" variants={stagger} initial="initial" animate="animate">
      <PageHeader title="Document Library" description="Ingest, index and manage your document corpus for AI-powered analysis.">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs" onClick={handleOpenFilePicker} disabled={uploadInProgress}>
          {uploadInProgress ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Upload className="w-3.5 h-3.5 mr-2" />} Upload Documents
        </Button>
      </PageHeader>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.csv,.txt,.md,.py"
        className="hidden"
        onChange={(event) => handleFilesSelected(event.target.files)}
      />

      {/* Stats */}
      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Total Documents" value={isLoading ? '—' : (summary?.total_documents ?? 0)} icon={FileText} glowColor="primary" />
        <MetricCard label="Indexed" value={isLoading ? '—' : (summary?.indexed_documents ?? 0)} icon={Check} glowColor="success" />
        <MetricCard label="Total Chunks" value={isLoading ? '—' : ((summary?.total_chunks ?? 0).toLocaleString())} icon={Layers} glowColor="accent" />
        <MetricCard label="Characters" value={isLoading ? '—' : `${Math.round((summary?.total_chars ?? 0) / 1000)}K`} icon={Database} glowColor="warning" />
      </motion.div>

      {uploadFeedback && (
        <motion.div variants={item} className={`glass rounded-xl p-4 mb-6 border ${uploadFeedback.type === 'success' ? 'border-glow-success/20' : uploadFeedback.type === 'info' ? 'border-primary/20' : 'border-glow-warning/20'}`}>
          <div className={`flex items-center gap-2 text-xs ${uploadFeedback.type === 'success' ? 'text-glow-success' : uploadFeedback.type === 'info' ? 'text-primary' : 'text-glow-warning'}`}>
            {uploadFeedback.type === 'success' ? <Check className="w-4 h-4" /> : uploadFeedback.type === 'info' ? <Loader2 className="w-4 h-4 animate-spin" /> : <AlertCircle className="w-4 h-4" />}
            {uploadFeedback.message}
          </div>
        </motion.div>
      )}

      {isError && (
        <motion.div variants={item} className="glass rounded-xl p-4 border border-glow-warning/20 mb-6">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertCircle className="w-4 h-4" />
            Product API unavailable. The Document Library cannot load real corpus data right now.
          </div>
        </motion.div>
      )}

      {/* Pipeline Visualization */}
      <motion.div variants={item}>
        <GlassCard className="mb-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Ingestion Pipeline</h3>
              <p className="text-xs text-muted-foreground mt-1">{pipelineStatusMessage}</p>
            </div>
            {pipelineJob?.status && <StatusPill status={pipelineJob.status === 'queued' ? 'running' : pipelineJob.status} />}
          </div>
          <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
            {pipelineSteps.map((step) => {
              const runtimeStep = pipelineStageLookup.get(step.key);
              const status = runtimeStep?.status || 'pending';
              const detail = runtimeStep?.detail || (status === 'pending' ? 'Waiting for indexing to reach this step.' : null);
              const iconClass =
                status === 'completed'
                  ? 'bg-glow-success/10 text-glow-success'
                  : status === 'running'
                    ? 'bg-primary/10 text-primary'
                    : status === 'error'
                      ? 'bg-glow-error/10 text-glow-error'
                      : 'bg-secondary/40 text-muted-foreground';

              return (
                <div key={step.key} className="rounded-xl border border-border/50 bg-secondary/10 p-4">
                  <div className="flex items-start gap-3">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${iconClass}`}>
                      <step.icon className={`w-4 h-4 ${status === 'running' ? 'animate-pulse' : ''}`} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-foreground">{step.label}</span>
                        <StatusPill status={status} className="shrink-0" />
                      </div>
                      <p className="text-[10px] text-muted-foreground leading-relaxed">{detail || 'Completed.'}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </motion.div>

      {/* Upload Zone */}
      <motion.div variants={item}>
        <div
          className={`border-2 border-dashed rounded-xl p-8 mb-6 text-center transition-colors group cursor-pointer ${dropActive ? 'border-primary/60 bg-primary/5' : 'border-border/60 hover:border-primary/40'} ${uploadMutation.isPending ? 'opacity-80' : ''}`}
          onClick={handleOpenFilePicker}
          onDragOver={(event) => {
            event.preventDefault();
            if (!uploadInProgress) setDropActive(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setDropActive(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setDropActive(false);
            if (uploadInProgress) return;
            handleFilesSelected(event.dataTransfer.files);
          }}
        >
          {uploadInProgress ? (
            <Loader2 className="w-8 h-8 text-primary mx-auto mb-3 animate-spin" />
          ) : (
            <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-3 group-hover:text-primary transition-colors" />
          )}
          <p className="text-sm text-foreground mb-1">Drop files here or click to browse</p>
          <p className="text-xs text-muted-foreground">Supported now: PDF, CSV, TXT, MD and PY — files are indexed immediately after upload.</p>
        </div>
      </motion.div>

      {/* Controls */}
      <motion.div variants={item} className="flex items-center justify-between mb-4 gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input placeholder="Search documents..." value={search} onChange={e => setSearch(e.target.value)}
            className="pl-9 h-8 text-xs bg-secondary/30 border-border/50" />
        </div>
        <div className="flex items-center gap-1 bg-secondary/30 rounded-lg p-0.5">
          <button onClick={() => setView('table')} className={`p-1.5 rounded-md transition-colors ${view === 'table' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
            <List className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setView('grid')} className={`p-1.5 rounded-md transition-colors ${view === 'grid' ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
            <Grid className="w-3.5 h-3.5" />
          </button>
        </div>
      </motion.div>

      {/* Document Table */}
      {view === 'table' ? (
        <motion.div variants={item} className="glass rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50">
                {['Document', 'Type', 'Status', 'Chunks', 'Characters', 'Loader', 'Indexed', 'Actions'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc, i) => (
                <motion.tr key={doc.document_id}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                  className="border-b border-border/30 hover:bg-secondary/20 transition-colors cursor-pointer group"
                  onClick={() => setSelectedDocument(doc)}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                      <span className="text-xs text-foreground group-hover:text-primary transition-colors truncate max-w-[240px]">{doc.name}</span>
                      {doc.warnings?.length > 0 && <AlertTriangle className="w-3 h-3 text-glow-warning shrink-0" />}
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">{(doc.file_type || '—').toUpperCase()}</span></td>
                  <td className="px-4 py-3"><StatusPill status={doc.status} /></td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{doc.chunk_count || '—'}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{doc.char_count ? doc.char_count.toLocaleString() : '—'}</td>
                  <td className="px-4 py-3"><span className="text-[10px] font-mono text-muted-foreground">{doc.loader_strategy_label || '—'}</span></td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{doc.indexed_at ? new Date(doc.indexed_at).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      disabled={deleteMutation.isPending}
                      onClick={(event) => {
                        event.stopPropagation();
                        requestDeleteDocument(doc);
                      }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </td>
                </motion.tr>
              ))}
              {!filtered.length && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-xs text-muted-foreground">
                    {emptyStateMessage}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </motion.div>
      ) : (
        <motion.div variants={item} className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((doc, i) => (
            <motion.div key={doc.document_id} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.04 }}
              className="glass rounded-xl p-4 cursor-pointer hover:border-primary/30 transition-all duration-300 group"
              onClick={() => setSelectedDocument(doc)}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-muted-foreground" />
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">{(doc.file_type || '—').toUpperCase()}</span>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill status={doc.status} />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-destructive"
                    disabled={deleteMutation.isPending}
                    onClick={(event) => {
                      event.stopPropagation();
                      requestDeleteDocument(doc);
                    }}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
              <h4 className="text-xs font-medium text-foreground mb-2 group-hover:text-primary transition-colors truncate">{doc.name}</h4>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <span>{doc.chunk_count} chunks</span>
                <span>{doc.size_label || '—'}</span>
              </div>
              {doc.warnings?.length > 0 && (
                <div className="mt-2 text-[10px] text-glow-warning truncate">{doc.warnings[0]}</div>
              )}
            </motion.div>
          ))}
          {!filtered.length && (
            <GlassCard className="md:col-span-2 lg:col-span-3">
              <div className="text-xs text-muted-foreground">{emptyStateMessage}</div>
            </GlassCard>
          )}
        </motion.div>
      )}

      <Sheet open={Boolean(selectedDocument)} onOpenChange={(open) => { if (!open) setSelectedDocument(null); }}>
        <SheetContent className="w-[440px] bg-card border-border overflow-y-auto sm:max-w-[440px]">
          <SheetHeader>
            <SheetTitle className="text-sm flex items-start gap-2 pr-8">
              <FileText className="w-4 h-4 mt-0.5 text-primary" />
              <span className="break-words">{selectedDocument?.name || 'Document details'}</span>
            </SheetTitle>
            <SheetDescription>
              Ingestion metadata, indexing status and document diagnostics from the real product corpus.
            </SheetDescription>
          </SheetHeader>

          {selectedDocument && (
            <div className="mt-6 space-y-5 text-sm">
              <div className="flex items-center justify-between gap-3">
                <StatusPill status={selectedDocument.status} />
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{(selectedDocument.file_type || 'unknown').toUpperCase()}</span>
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    className="h-8 px-3 text-[11px]"
                    disabled={deleteMutation.isPending}
                    onClick={() => requestDeleteDocument(selectedDocument)}
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                    Delete
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <GlassCard className="p-4">
                  <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground"><Layers className="w-3.5 h-3.5" /> Chunks</div>
                  <div className="text-lg font-semibold text-foreground">{selectedDocument.chunk_count.toLocaleString()}</div>
                </GlassCard>
                <GlassCard className="p-4">
                  <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground"><HardDrive className="w-3.5 h-3.5" /> Size</div>
                  <div className="text-lg font-semibold text-foreground">{selectedDocument.size_label || '—'}</div>
                </GlassCard>
                <GlassCard className="p-4">
                  <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground"><Database className="w-3.5 h-3.5" /> Characters</div>
                  <div className="text-lg font-semibold text-foreground">{selectedDocument.char_count.toLocaleString()}</div>
                </GlassCard>
                <GlassCard className="p-4">
                  <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground"><ScanSearch className="w-3.5 h-3.5" /> Pages</div>
                  <div className="text-lg font-semibold text-foreground">{selectedDocument.page_count ?? '—'}</div>
                </GlassCard>
              </div>

              <Separator />

              <div className="space-y-3">
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Document metadata</h4>
                <div className="space-y-2 text-xs">
                  <div className="flex items-start justify-between gap-3"><span className="text-muted-foreground">Document ID</span><span className="text-foreground font-mono text-right break-all max-w-[240px]">{selectedDocument.document_id}</span></div>
                  <div className="flex items-start justify-between gap-3"><span className="text-muted-foreground">Loader</span><span className="text-foreground text-right">{selectedDocument.loader_strategy_label || '—'}</span></div>
                  <div className="flex items-start justify-between gap-3"><span className="text-muted-foreground">Indexed at</span><span className="text-foreground text-right">{formatDate(selectedDocument.indexed_at)}</span></div>
                  <div className="flex items-start justify-between gap-3"><span className="text-muted-foreground">Source type</span><span className="text-foreground text-right">{selectedDocument.source_type || '—'}</span></div>
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Warnings & diagnostics</h4>
                {selectedDocument.warnings.length ? (
                  <div className="space-y-2">
                    {selectedDocument.warnings.map((warning) => (
                      <div key={warning} className="rounded-lg border border-glow-warning/20 bg-glow-warning/5 px-3 py-2 text-xs text-glow-warning flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                        <span>{warning}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-border/50 bg-secondary/20 px-3 py-3 text-xs text-muted-foreground flex items-start gap-2">
                    <FileSearch className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    No document-level warnings were recorded for this indexed item.
                  </div>
                )}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      <AlertDialog open={Boolean(documentPendingDelete)} onOpenChange={(open) => { if (!open && !deleteMutation.isPending) setDocumentPendingDelete(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove <strong>{documentPendingDelete?.name}</strong> from the indexed corpus and update the Document Library immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
              onClick={(event) => {
                event.preventDefault();
                confirmDeleteDocument();
              }}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete document'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </motion.div>
  );
}

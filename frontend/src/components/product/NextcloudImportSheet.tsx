import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Check, CheckSquare, ChevronRight, Eye, FileText, Files, Folder, FolderTree, Import, Loader2, Search, Square, XCircle } from 'lucide-react';

import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { toast } from '@/components/ui/sonner';
import {
  getProductNextcloudDocuments,
  buildProductNextcloudOpenUrl,
  importProductDocumentsFromNextcloud,
  type ProductNextcloudDocument,
  type ProductUploadDocumentsResponse,
} from '@/lib/product-api';

type NextcloudImportSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportStarted?: (payload: ProductUploadDocumentsResponse) => void;
};

type FolderNode = {
  name: string;
  path: string;
  children: Map<string, FolderNode>;
  files: ProductNextcloudDocument[];
};

const STARTER_FILE_HINTS = [
  'Master Service Agreement v4.2.pdf',
  'Information Security Policy v3.1.pdf',
  'Information Security Policy v3.2.pdf',
  'Governance Committee Minutes and Action Items.pdf',
  'Internal Audit Checklist - Vendor Controls.pdf',
  'AUD-001_Internal_Audit_Checklist_Vendor_Controls.pdf',
  'Nonconformance Report - Vendor Access Review.pdf',
  'AUD-002_Nonconformance_Report_Vendor_Access_Review.pdf',
  'Remediation Closure Note - Vendor Access Review.pdf',
  'Sarah Chen - Senior ML Engineer CV.pdf',
  'Senior ML Engineer Role Brief.pdf',
];

const TOUR_COMPLETED_STORAGE_KEY = 'workbench-tour-document-library-complete';

function shouldPromptForWorkflowTour(): boolean {
  try {
    return window.localStorage.getItem(TOUR_COMPLETED_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function promptForWorkflowTourSoon() {
  if (!shouldPromptForWorkflowTour()) return;
  window.setTimeout(() => window.dispatchEvent(new CustomEvent('workbench-tour:ready-for-workflow-tour')), 220);
}

const SYNTHETIC_CORPUS_ALIASES = [
  'frontend demo grounded',
  'demo synthetic corpus',
  'demo synthetic',
  'synthetic demo',
  'synthetic corpus',
];
function createFolderNode(name: string, path: string): FolderNode {
  return { name, path, children: new Map(), files: [] };
}

function formatDate(value?: string | number | null): string {
  if (typeof value === 'number' && value > 0) return new Date(value * 1000).toLocaleString();
  if (typeof value === 'string' && value.trim()) {
    const normalized = value.includes('T') ? value : value.replace(' ', 'T');
    const parsed = new Date(normalized);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
  }
  return 'Unknown';
}

function formatSize(value?: number | null): string {
  if (!value || value <= 0) return '-';
  if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  if (value >= 1024) return `${Math.round(value / 1024)} KB`;
  return `${value} B`;
}

function buildFolderTree(documents: ProductNextcloudDocument[]): FolderNode {
  const root = createFolderNode('All files', '');
  for (const document of documents) {
    const parts = String(document.relative_path || '').trim().split('/').filter(Boolean);
    let current = root;
    let currentPath = '';
    for (const folder of parts.slice(0, -1)) {
      currentPath = currentPath ? `${currentPath}/${folder}` : folder;
      if (!current.children.has(folder)) current.children.set(folder, createFolderNode(folder, currentPath));
      current = current.children.get(folder)!;
    }
    current.files.push(document);
  }
  return root;
}

function flattenDocuments(node: FolderNode): ProductNextcloudDocument[] {
  const collected = [...node.files];
  for (const child of node.children.values()) collected.push(...flattenDocuments(child));
  return collected;
}

function findFolderNode(root: FolderNode, path: string): FolderNode {
  if (!path) return root;
  let current = root;
  for (const segment of path.split('/').filter(Boolean)) {
    const next = current.children.get(segment);
    if (!next) return root;
    current = next;
  }
  return current;
}

function findFolderByAliases(root: FolderNode, aliases: string[]): FolderNode | null {
  const normalizedAliases = aliases.map((alias) => alias.toLowerCase());
  const queue = [...root.children.values()];
  while (queue.length) {
    const node = queue.shift()!;
    const haystack = `${node.name} ${node.path}`.toLowerCase().replace(/[_-]+/g, ' ');
    if (normalizedAliases.some((alias) => haystack.includes(alias))) return node;
    queue.push(...node.children.values());
  }
  return null;
}

function normalizeDocumentKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function documentMatchesStarterHint(document: ProductNextcloudDocument, hint: string): boolean {
  const hintStem = hint.replace(/\.pdf$/i, '');
  const hintKey = normalizeDocumentKey(hintStem);
  const titleKey = normalizeDocumentKey(String(document.title || ''));
  const filenameKey = normalizeDocumentKey(String(document.relative_path || '').split('/').pop() || '');
  const pathKey = normalizeDocumentKey(String(document.relative_path || ''));
  return titleKey.includes(hintKey) || filenameKey.includes(hintKey) || pathKey.includes(hintKey);
}

function isSyntheticCorpusDocument(document: ProductNextcloudDocument): boolean {
  const haystack = String(document.relative_path || '').toLowerCase().replace(/[_-]+/g, ' ');
  return SYNTHETIC_CORPUS_ALIASES.some((alias) => haystack.includes(alias));
}

function truncate(value?: string | null, maxChars = 72): string {
  const normalized = String(value || '').trim();
  if (!normalized) return 'Untitled document';
  if (normalized.length <= maxChars) return normalized;
  return `${normalized.slice(0, maxChars - 1).trimEnd()}...`;
}

function humanizeFolderName(value: string): string {
  const normalized = String(value || '').split('/').filter(Boolean).pop() || 'Corpus folder';
  return normalized.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().replace(/\b\w/g, (character) => character.toUpperCase());
}

function isPdfDocument(document: ProductNextcloudDocument): boolean {
  const haystack = `${document.relative_path || ''} ${document.title || ''}`.toLowerCase();
  return haystack.endsWith('.pdf') || haystack.includes('.pdf ');
}

function toImportPayload(document: ProductNextcloudDocument) {
  return {
    relativePath: document.relative_path || undefined,
    documentId: document.document_id || undefined,
    filename: document.relative_path ? String(document.relative_path).split('/').pop() : undefined,
    title: document.title || undefined,
    category: document.category || undefined,
    webdavUrl: document.webdav_url || undefined,
  };
}

function isGuidedTourActive(): boolean {
  return new URLSearchParams(window.location.search).get('tour') === '1';
}

function preventTourOutsideDismiss(event: Event) {
  if (isGuidedTourActive()) event.preventDefault();
}

export function NextcloudImportSheet({ open, onOpenChange, onImportStarted }: NextcloudImportSheetProps) {
  const [search, setSearch] = useState('');
  const [currentPath, setCurrentPath] = useState('');
  const [focusedRelativePath, setFocusedRelativePath] = useState<string | null>(null);
  const [selectedRelativePaths, setSelectedRelativePaths] = useState<string[]>([]);
  const [tourFolderRequest, setTourFolderRequest] = useState<'root' | 'synthetic' | null>(null);
  const [pendingStarterSelection, setPendingStarterSelection] = useState(false);
  const sheetContentRef = useRef<HTMLDivElement | null>(null);
  const wasOpenRef = useRef(open);

  useEffect(() => {
    if (wasOpenRef.current && !open) promptForWorkflowTourSoon();
    wasOpenRef.current = open;
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleTourScrollTop = () => {
      window.requestAnimationFrame(() => {
        sheetContentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
      });
    };
    window.addEventListener('workbench-tour:nextcloud-scroll-top', handleTourScrollTop);
    return () => window.removeEventListener('workbench-tour:nextcloud-scroll-top', handleTourScrollTop);
  }, [open]);

  const nextcloudQuery = useQuery({
    queryKey: ['product-integrations', 'nextcloud-documents', 'library-import'],
    queryFn: () => getProductNextcloudDocuments(0),
    enabled: open,
    refetchOnWindowFocus: false,
  });

  const documents = nextcloudQuery.data?.documents ?? [];
  const root = useMemo(() => buildFolderTree(documents), [documents]);
  const activeFolder = useMemo(() => findFolderNode(root, currentPath), [root, currentPath]);
  const searchTerm = search.trim().toLowerCase();
  const documentByPath = useMemo(() => new Map(documents.map((document) => [String(document.relative_path || ''), document])), [documents]);
  const selectedPathSet = useMemo(() => new Set(selectedRelativePaths), [selectedRelativePaths]);
  const selectedDocuments = useMemo(
    () => selectedRelativePaths.map((path) => documentByPath.get(path)).filter(Boolean) as ProductNextcloudDocument[],
    [documentByPath, selectedRelativePaths],
  );

  const folderRows = useMemo(() => [...activeFolder.children.values()].map((node) => {
    const nestedDocuments = flattenDocuments(node);
    return {
      name: node.name,
      path: node.path,
      fileCount: nestedDocuments.length,
      pdfCount: nestedDocuments.filter(isPdfDocument).length,
    };
  }).sort((left, right) => left.name.localeCompare(right.name)), [activeFolder]);

  const visibleDocuments = useMemo(() => {
    const base = searchTerm ? flattenDocuments(root) : currentPath ? flattenDocuments(activeFolder) : flattenDocuments(root);
    return base.filter((document) => {
      if (!searchTerm) return true;
      const haystack = `${document.title} ${document.relative_path || ''} ${document.category || ''}`.toLowerCase();
      return haystack.includes(searchTerm);
    }).sort((left, right) => String(left.relative_path || left.title).localeCompare(String(right.relative_path || right.title)));
  }, [activeFolder, currentPath, root, searchTerm]);
  const visiblePdfDocuments = useMemo(() => visibleDocuments.filter(isPdfDocument), [visibleDocuments]);

  const focusSyntheticCorpus = useCallback(() => {
    const syntheticFolder = findFolderByAliases(root, SYNTHETIC_CORPUS_ALIASES);
    if (syntheticFolder) {
      setCurrentPath(syntheticFolder.path);
      setSearch('');
      setFocusedRelativePath(null);
    }
  }, [root]);

  const selectStarterSet = useCallback(() => {
    if (!documents.length) {
      setPendingStarterSelection(true);
      return;
    }

    const nextPaths: string[] = [];
    for (const hint of STARTER_FILE_HINTS) {
      const matches = documents
        .filter((document) => isPdfDocument(document) && documentMatchesStarterHint(document, hint))
        .sort((left, right) => Number(isSyntheticCorpusDocument(right)) - Number(isSyntheticCorpusDocument(left)));
      const relativePath = String(matches[0]?.relative_path || '');
      if (relativePath) nextPaths.push(relativePath);
    }

    const uniquePaths = Array.from(new Set(nextPaths));
    if (!uniquePaths.length) {
      setPendingStarterSelection(false);
      toast.error('The recommended starter PDFs are not visible in the current Nextcloud listing yet. Refresh the corpus and try again.');
      return;
    }

    setSelectedRelativePaths((current) => Array.from(new Set([...current, ...uniquePaths])));
    setFocusedRelativePath(uniquePaths[0]);
    setPendingStarterSelection(false);
    focusSyntheticCorpus();

    const missingCount = STARTER_FILE_HINTS.length - uniquePaths.length;
    if (missingCount > 0) {
      toast.warning(`${uniquePaths.length} recommended starter PDF(s) selected. ${missingCount} could not be matched in the current listing.`);
    } else {
      toast.success(`${uniquePaths.length} recommended starter PDF(s) selected.`);
    }
  }, [documents, focusSyntheticCorpus]);

  useEffect(() => {
    if (!open) return;
    if (!visibleDocuments.length) {
      setFocusedRelativePath(null);
      return;
    }
    const hasFocus = focusedRelativePath && visibleDocuments.some((document) => String(document.relative_path || '') === focusedRelativePath);
    if (!hasFocus) setFocusedRelativePath(String(visibleDocuments[0].relative_path || ''));
  }, [focusedRelativePath, open, visibleDocuments]);

  useEffect(() => {
    if (!open) {
      setSearch('');
      setCurrentPath('');
      setFocusedRelativePath(null);
      setSelectedRelativePaths([]);
      setTourFolderRequest(null);
      setPendingStarterSelection(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleFocusFolder = (event: Event) => {
      const detail = (event as CustomEvent<{ kind?: string }>).detail;
      setTourFolderRequest(detail?.kind === 'synthetic' ? 'synthetic' : 'root');
    };
    const handleSelectStarter = () => {
      setPendingStarterSelection(true);
      selectStarterSet();
    };

    window.addEventListener('workbench-tour:focus-nextcloud-folder', handleFocusFolder as EventListener);
    window.addEventListener('workbench-tour:select-nextcloud-starter-set', handleSelectStarter);
    return () => {
      window.removeEventListener('workbench-tour:focus-nextcloud-folder', handleFocusFolder as EventListener);
      window.removeEventListener('workbench-tour:select-nextcloud-starter-set', handleSelectStarter);
    };
  }, [open, selectStarterSet]);

  useEffect(() => {
    if (!open || !tourFolderRequest) return;
    if (tourFolderRequest === 'root') {
      setSearch('');
      setCurrentPath('');
      setFocusedRelativePath(null);
      setTourFolderRequest(null);
      return;
    }

    const syntheticFolder = findFolderByAliases(root, SYNTHETIC_CORPUS_ALIASES);
    if (syntheticFolder) {
      setSearch('');
      setCurrentPath(syntheticFolder.path);
      setFocusedRelativePath(null);
      setTourFolderRequest(null);
    }
  }, [open, root, tourFolderRequest]);

  useEffect(() => {
    if (!open || !pendingStarterSelection || !documents.length) return;
    selectStarterSet();
  }, [documents.length, open, pendingStarterSelection, selectStarterSet]);

  const focusedDocument = useMemo(
    () => documentByPath.get(String(focusedRelativePath || '')) ?? selectedDocuments[0] ?? null,
    [documentByPath, focusedRelativePath, selectedDocuments],
  );

  const importMutation = useMutation({
    mutationFn: async (documentsToImport: ProductNextcloudDocument[]) => importProductDocumentsFromNextcloud(documentsToImport.map(toImportPayload)),
    onSuccess: (payload) => {
      onImportStarted?.(payload);
      toast.success(payload.message || 'Import accepted. Preparing ingestion pipeline.');
      onOpenChange(false);
      promptForWorkflowTourSoon();
    },
    onError: (error) => {
      const count = selectedDocuments.length;
      const fallbackMessage = count > 1
        ? `Could not import ${count} selected files from Nextcloud.`
        : focusedDocument
          ? `Could not import ${focusedDocument.title || focusedDocument.relative_path || 'the selected file'} from Nextcloud.`
          : 'Nextcloud import failed.';
      toast.error(error instanceof Error ? error.message : fallbackMessage);
    },
  });

  const toggleDocumentSelection = (document: ProductNextcloudDocument) => {
    const relativePath = String(document.relative_path || '');
    if (!relativePath || importMutation.isPending) return;
    setFocusedRelativePath(relativePath);
    if (!isPdfDocument(document)) {
      toast.error('Only PDFs can be imported in this public demo flow.');
      return;
    }
    setSelectedRelativePaths((current) => current.includes(relativePath) ? current.filter((path) => path !== relativePath) : [...current, relativePath]);
  };

  const addDocumentsToSelection = (documentsToAdd: ProductNextcloudDocument[]) => {
    const nextPaths = documentsToAdd.filter(isPdfDocument).map((document) => String(document.relative_path || '')).filter(Boolean);
    if (!nextPaths.length) return;
    setSelectedRelativePaths((current) => Array.from(new Set([...current, ...nextPaths])));
    setFocusedRelativePath(nextPaths[0]);
  };

  const handleOpenRemote = (document: ProductNextcloudDocument | null = focusedDocument) => {
    if (!document) return;
    const previewWindow = window.open(buildProductNextcloudOpenUrl(toImportPayload(document)), '_blank');
    if (!previewWindow) toast.error('The browser blocked the remote preview tab. Allow pop-ups for this site and try again.');
  };

  const breadcrumbs = currentPath.split('/').filter(Boolean);
  const activeLabel = currentPath ? humanizeFolderName(breadcrumbs[breadcrumbs.length - 1]) : 'All files';
  const selectedPdfCount = selectedDocuments.filter(isPdfDocument).length;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent ref={sheetContentRef} className="w-[920px] max-w-[96vw] overflow-y-auto border-border bg-card sm:max-w-[920px]" onInteractOutside={preventTourOutsideDismiss}>
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-sm">
            <FolderTree className="h-4 w-4 text-primary" /> Import from Nextcloud
          </SheetTitle>
          <SheetDescription>
            Browse folders, select one or more PDFs, preview individual files when useful, then import the selected batch into the Document Library.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-5 space-y-4" data-testid="nextcloud-import-sheet">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search PDFs, folders, or document names..."
                className="h-9 border-border/50 bg-secondary/20 pl-9 text-xs"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
              <StatusPill status={nextcloudQuery.data?.status || 'pending'} />
              <span>{nextcloudQuery.data?.entry_count ?? 0} file(s)</span>
              <span>{selectedDocuments.length} selected</span>
            </div>
          </div>

          <GlassCard className="p-3">
            <div className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
              <button
                type="button"
                className={`rounded px-2 py-1 ${!currentPath ? 'bg-secondary/40 text-foreground' : 'hover:bg-secondary/40'}`}
                onClick={() => setCurrentPath('')}
              >
                All files
              </button>
              {breadcrumbs.map((segment, index) => {
                const path = breadcrumbs.slice(0, index + 1).join('/');
                return (
                  <div key={path} className="flex items-center gap-1">
                    <ChevronRight className="h-3 w-3" />
                    <button
                      type="button"
                      className={`rounded px-2 py-1 ${currentPath === path ? 'bg-secondary/40 text-foreground' : 'hover:bg-secondary/40'}`}
                      onClick={() => setCurrentPath(path)}
                    >
                      {humanizeFolderName(segment)}
                    </button>
                  </div>
                );
              })}
            </div>
          </GlassCard>

          <div className="grid gap-4 lg:grid-cols-[0.88fr_1.45fr]">
            <GlassCard className="p-3" data-tour="nextcloud-folder-list">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-foreground">Folders</p>
                  <p className="text-[10px] text-muted-foreground">Open a corpus folder, then choose the PDFs you want from the file list.</p>
                </div>
                {currentPath ? (
                  <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => setCurrentPath(currentPath.split('/').slice(0, -1).join('/'))}>
                    Up
                  </Button>
                ) : null}
              </div>
              <div className="max-h-[52vh] space-y-1.5 overflow-y-auto pr-1" data-testid="nextcloud-folder-list">
                <button
                  type="button"
                  className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left ${!currentPath ? 'border-primary/50 bg-primary/5' : 'border-border/40 bg-secondary/10 hover:border-primary/30 hover:bg-secondary/20'}`}
                  onClick={() => {
                    setCurrentPath('');
                    setFocusedRelativePath(null);
                  }}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <FolderTree className="h-3.5 w-3.5 shrink-0 text-primary" />
                    <span className="truncate text-xs text-foreground">All files</span>
                  </span>
                  <span className="text-[10px] text-muted-foreground">{documents.length}</span>
                </button>
                {folderRows.length ? folderRows.map((folder) => (
                  <button
                    key={folder.path}
                    type="button"
                    className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left ${currentPath === folder.path ? 'border-primary/50 bg-primary/5' : 'border-border/40 bg-secondary/10 hover:border-primary/30 hover:bg-secondary/20'}`}
                    onClick={() => {
                      setCurrentPath(folder.path);
                      setFocusedRelativePath(null);
                    }}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <Folder className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span className="truncate text-xs text-foreground">{humanizeFolderName(folder.name)}</span>
                    </span>
                    <span className="shrink-0 text-[10px] text-muted-foreground">{folder.pdfCount} PDF - {folder.fileCount}</span>
                  </button>
                )) : <p className="text-xs text-muted-foreground">{searchTerm ? 'Search mode shows matching files directly.' : 'No subfolders here.'}</p>}
              </div>
            </GlassCard>

            <GlassCard className="p-3" data-tour="nextcloud-file-selection">
              <div className="mb-3 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                <div>
                  <p className="text-xs font-medium text-foreground">Files</p>
                  <p className="text-[10px] text-muted-foreground">{searchTerm ? 'Showing matches across the whole corpus.' : `Showing files under ${activeLabel}.`}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/50 bg-background/20 p-1" data-tour="nextcloud-selection-controls">
                    <span className="px-2">{visibleDocuments.length} visible</span>
                    {nextcloudQuery.isFetching ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
                    <Button variant="outline" size="sm" className="h-7 text-[10px]" disabled={!visiblePdfDocuments.length || importMutation.isPending} onClick={() => addDocumentsToSelection(visiblePdfDocuments)}>
                      <Files className="mr-1 h-3 w-3" /> Select all shown PDFs
                    </Button>
                  </div>
                  <Button variant="ghost" size="sm" className="h-7 text-[10px] text-muted-foreground" disabled={!selectedDocuments.length || importMutation.isPending} onClick={() => setSelectedRelativePaths([])}>
                    <XCircle className="mr-1 h-3 w-3" /> Clear
                  </Button>
                </div>
              </div>
              <div className="max-h-[52vh] space-y-2 overflow-y-auto pr-1" data-testid="nextcloud-file-list">
                {visibleDocuments.length ? visibleDocuments.map((document) => {
                  const relativePath = String(document.relative_path || '');
                  const selected = selectedPathSet.has(relativePath);
                  const focused = relativePath === focusedRelativePath;
                  const pdf = isPdfDocument(document);
                  return (
                    <div
                      key={`${relativePath || document.title}-${document.modified_at || 'remote'}`}
                      role="button"
                      tabIndex={0}
                      className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${selected ? 'border-primary/60 bg-primary/5 shadow-[0_0_24px_-18px_hsl(var(--primary))]' : focused ? 'border-primary/30 bg-secondary/20' : 'border-border/40 bg-secondary/10 hover:border-primary/30 hover:bg-secondary/20'}`}
                      onClick={() => toggleDocumentSelection(document)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          toggleDocumentSelection(document);
                        }
                      }}
                      data-testid={selected ? 'nextcloud-document-selected' : undefined}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 items-start gap-3">
                          <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border ${selected ? 'border-primary bg-primary text-primary-foreground' : 'border-border/70 bg-background/50 text-muted-foreground'}`}>
                            {selected ? <Check className="h-3 w-3" /> : pdf ? <Square className="h-3 w-3" /> : <FileText className="h-3 w-3" />}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-xs font-medium text-foreground">{truncate(document.title, 88)}</p>
                            <p className="mt-1 break-all text-[10px] text-muted-foreground">{relativePath || 'remote file'}</p>
                          </div>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-1">
                          {pdf ? <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider text-primary">PDF</span> : null}
                          {selected ? <CheckSquare className="h-3.5 w-3.5 text-primary" /> : <FileText className="h-3.5 w-3.5 text-muted-foreground" />}
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted-foreground">
                        <div className="flex flex-wrap items-center gap-3">
                          <span>{document.category || 'document'}</span>
                          <span>{formatSize(document.size_bytes)}</span>
                          <span>Updated {formatDate(document.modified_at)}</span>
                        </div>
                        <button
                          type="button"
                          className="inline-flex items-center rounded-md border border-border/60 bg-background/40 px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                          onClick={(event) => {
                            event.stopPropagation();
                            setFocusedRelativePath(relativePath);
                            handleOpenRemote(document);
                          }}
                        >
                          <Eye className="mr-1 h-3 w-3" /> View
                        </button>
                      </div>
                    </div>
                  );
                }) : <p data-testid="nextcloud-file-list-empty" className="text-xs text-muted-foreground">No files match this folder/search view yet.</p>}
              </div>
            </GlassCard>
          </div>

          <GlassCard className="sticky bottom-0 z-20 border-primary/20 bg-card/95 p-3 backdrop-blur-xl" data-tour="nextcloud-import-action">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-foreground">Selected import batch</p>
                <p className="mt-1 break-all text-[10px] text-muted-foreground">
                  {selectedDocuments.length
                    ? `${selectedDocuments.length} file(s) selected - ${selectedPdfCount} PDF(s). ${selectedDocuments.slice(0, 2).map((document) => document.relative_path).join(' - ')}${selectedDocuments.length > 2 ? ' - ...' : ''}`
                    : 'Choose one or more PDFs from the list above. You can move across folders before importing.'}
                </p>
              </div>
              <Button
                size="sm"
                className="h-8 text-[10px]"
                disabled={!selectedDocuments.length || importMutation.isPending}
                onClick={() => selectedDocuments.length && importMutation.mutate(selectedDocuments)}
              >
                {importMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Import className="mr-1 h-3.5 w-3.5" />}
                Import {selectedDocuments.length || ''} into Document Library
              </Button>
            </div>
          </GlassCard>
        </div>
      </SheetContent>
    </Sheet>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ChevronRight, ExternalLink, FileText, Folder, FolderTree, Import, Loader2, Search } from 'lucide-react';

import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { toast } from '@/components/ui/sonner';
import {
  getProductNextcloudDocuments,
  buildProductNextcloudOpenUrl,
  importProductDocumentFromNextcloud,
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

function createFolderNode(name: string, path: string): FolderNode {
  return { name, path, children: new Map(), files: [] };
}

function formatDate(value?: string | number | null): string {
  if (typeof value === 'number' && value > 0) {
    return new Date(value * 1000).toLocaleString();
  }
  if (typeof value === 'string' && value.trim()) {
    const normalized = value.includes('T') ? value : value.replace(' ', 'T');
    const parsed = new Date(normalized);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
  }
  return 'Unknown';
}

function formatSize(value?: number | null): string {
  if (!value || value <= 0) return '—';
  if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  if (value >= 1024) return `${Math.round(value / 1024)} KB`;
  return `${value} B`;
}

function buildFolderTree(documents: ProductNextcloudDocument[]): FolderNode {
  const root = createFolderNode('All files', '');
  for (const document of documents) {
    const relativePath = String(document.relative_path || '').trim();
    const parts = relativePath.split('/').filter(Boolean);
    const folders = parts.slice(0, -1);
    let current = root;
    let currentPath = '';
    for (const folder of folders) {
      currentPath = currentPath ? `${currentPath}/${folder}` : folder;
      if (!current.children.has(folder)) {
        current.children.set(folder, createFolderNode(folder, currentPath));
      }
      current = current.children.get(folder)!;
    }
    current.files.push(document);
  }
  return root;
}

function flattenDocuments(node: FolderNode): ProductNextcloudDocument[] {
  const collected = [...node.files];
  for (const child of node.children.values()) {
    collected.push(...flattenDocuments(child));
  }
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

function truncate(value?: string | null, maxChars = 72): string {
  const normalized = String(value || '').trim();
  if (!normalized) return 'Untitled document';
  if (normalized.length <= maxChars) return normalized;
  return `${normalized.slice(0, maxChars - 1).trimEnd()}…`;
}

export function NextcloudImportSheet({ open, onOpenChange, onImportStarted }: NextcloudImportSheetProps) {
  const [search, setSearch] = useState('');
  const [currentPath, setCurrentPath] = useState('');
  const [selectedRelativePath, setSelectedRelativePath] = useState<string | null>(null);

  const nextcloudQuery = useQuery({
    queryKey: ['product-integrations', 'nextcloud-documents', 'library-import'],
    queryFn: () => getProductNextcloudDocuments(200),
    enabled: open,
    refetchOnWindowFocus: false,
  });

  const importMutation = useMutation({
    mutationFn: async (document: ProductNextcloudDocument) => {
      return importProductDocumentFromNextcloud({
        relativePath: document.relative_path || undefined,
        documentId: document.document_id || undefined,
        filename: document.relative_path ? String(document.relative_path).split('/').pop() : undefined,
        title: document.title || undefined,
        category: document.category || undefined,
        webdavUrl: document.webdav_url || undefined,
      });
    },
    onSuccess: (payload) => {
      onImportStarted?.(payload);
      toast.success(payload.message || 'Import accepted. Preparing ingestion pipeline.');
      onOpenChange(false);
    },
    onError: (error) => {
      const fallbackMessage = selectedDocument
        ? `Could not import ${selectedDocument.title || selectedDocument.relative_path || 'the selected file'} from Nextcloud.`
        : 'Nextcloud import failed.';
      toast.error(error instanceof Error ? error.message : fallbackMessage);
    },
  });

  const documents = nextcloudQuery.data?.documents ?? [];
  const root = useMemo(() => buildFolderTree(documents), [documents]);
  const activeFolder = useMemo(() => findFolderNode(root, currentPath), [root, currentPath]);
  const searchTerm = search.trim().toLowerCase();

  const folderRows = useMemo(() => {
    const folders = [...activeFolder.children.values()]
      .map((node) => ({
        name: node.name,
        path: node.path,
        fileCount: flattenDocuments(node).length,
      }))
      .sort((left, right) => left.name.localeCompare(right.name));
    return folders;
  }, [activeFolder]);

  const visibleDocuments = useMemo(() => {
    const base = searchTerm
      ? flattenDocuments(root)
      : currentPath
        ? flattenDocuments(activeFolder)
        : flattenDocuments(root);
    return base
      .filter((document) => {
        if (!searchTerm) return true;
        const haystack = `${document.title} ${document.relative_path || ''} ${document.category || ''}`.toLowerCase();
        return haystack.includes(searchTerm);
      })
      .sort((left, right) => String(left.relative_path || left.title).localeCompare(String(right.relative_path || right.title)));
  }, [activeFolder, currentPath, root, searchTerm]);

  useEffect(() => {
    if (!open) return;
    if (!visibleDocuments.length) {
      setSelectedRelativePath(null);
      return;
    }
    const hasSelection = selectedRelativePath && visibleDocuments.some((document) => String(document.relative_path || '') === selectedRelativePath);
    if (!hasSelection) {
      setSelectedRelativePath(String(visibleDocuments[0].relative_path || ''));
    }
  }, [open, selectedRelativePath, visibleDocuments]);

  const selectedDocument = useMemo(
    () => documents.find((document) => String(document.relative_path || '') === selectedRelativePath) ?? null,
    [documents, selectedRelativePath],
  );

  const handleOpenRemote = () => {
    if (!selectedDocument) return;

    const remoteUrl = buildProductNextcloudOpenUrl({
      relativePath: selectedDocument.relative_path || undefined,
      documentId: selectedDocument.document_id || undefined,
      filename: selectedDocument.relative_path ? String(selectedDocument.relative_path).split('/').pop() : undefined,
      title: selectedDocument.title || undefined,
      category: selectedDocument.category || undefined,
      webdavUrl: selectedDocument.webdav_url || undefined,
    });

    const previewWindow = window.open(remoteUrl, '_blank');
    if (!previewWindow) {
      toast.error('The browser blocked the remote preview tab. Allow pop-ups for this site and try again.');
    }
  };

  const breadcrumbs = currentPath.split('/').filter(Boolean);
  const activeLabel = currentPath ? breadcrumbs[breadcrumbs.length - 1] : 'All files';

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[820px] max-w-[96vw] overflow-y-auto border-border bg-card sm:max-w-[820px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-sm">
            <FolderTree className="h-4 w-4 text-primary" /> Import from Nextcloud
          </SheetTitle>
          <SheetDescription>
            Browse the remote evidence corpus by folder, preview the matching files, then import one file into the Document Library for indexing.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-5 space-y-4" data-testid="nextcloud-import-sheet">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search the Nextcloud corpus..."
                className="h-9 border-border/50 bg-secondary/20 pl-9 text-xs"
              />
            </div>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
              <StatusPill status={nextcloudQuery.data?.status || 'pending'} />
              <span>{nextcloudQuery.data?.entry_count ?? 0} file(s)</span>
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
                      {segment}
                    </button>
                  </div>
                );
              })}
            </div>
          </GlassCard>

          <div className="grid gap-4 lg:grid-cols-[0.88fr_1.45fr]">
            <GlassCard className="p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-foreground">Folders</p>
                  <p className="text-[10px] text-muted-foreground">Explore the remote corpus with folders and breadcrumbs.</p>
                </div>
                {currentPath ? (
                  <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => setCurrentPath(currentPath.split('/').slice(0, -1).join('/'))}>
                    Up
                  </Button>
                ) : null}
              </div>
              <div className="space-y-1.5" data-testid="nextcloud-folder-list">
                <button
                  type="button"
                  className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left ${!currentPath ? 'border-primary/50 bg-primary/5' : 'border-border/40 bg-secondary/10 hover:border-primary/30 hover:bg-secondary/20'}`}
                  onClick={() => {
                    setCurrentPath('');
                    setSelectedRelativePath(null);
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
                      setSelectedRelativePath(null);
                    }}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <Folder className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span className="truncate text-xs text-foreground">{folder.name}</span>
                    </span>
                    <span className="text-[10px] text-muted-foreground">{folder.fileCount}</span>
                  </button>
                )) : <p className="text-xs text-muted-foreground">{searchTerm ? 'Search mode shows matching files directly.' : 'No subfolders here.'}</p>}
              </div>
            </GlassCard>

            <GlassCard className="p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-foreground">Files</p>
                  <p className="text-[10px] text-muted-foreground">{searchTerm ? 'Showing matches across the whole corpus.' : `Showing files under ${activeLabel}.`}</p>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span>{visibleDocuments.length} visible</span>
                  {nextcloudQuery.isFetching ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
                </div>
              </div>
              <div className="space-y-2" data-testid="nextcloud-file-list">
                {visibleDocuments.length ? visibleDocuments.map((document) => {
                  const relativePath = String(document.relative_path || '');
                  const selected = relativePath === selectedRelativePath;
                  return (
                    <button
                      key={`${relativePath || document.title}-${document.modified_at || 'remote'}`}
                      type="button"
                      className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${selected ? 'border-primary/60 bg-primary/5' : 'border-border/40 bg-secondary/10 hover:border-primary/30 hover:bg-secondary/20'}`}
                      onClick={() => setSelectedRelativePath(relativePath)}
                      data-testid={selected ? 'nextcloud-document-selected' : undefined}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-xs font-medium text-foreground">{truncate(document.title, 88)}</p>
                          <p className="mt-1 break-all text-[10px] text-muted-foreground">{relativePath || 'remote file'}</p>
                        </div>
                        <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-muted-foreground">
                        <span>{document.category || 'document'}</span>
                        <span>{formatSize(document.size_bytes)}</span>
                        <span>Updated {formatDate(document.modified_at)}</span>
                      </div>
                    </button>
                  );
                }) : <p data-testid="nextcloud-file-list-empty" className="text-xs text-muted-foreground">No files match this folder/search view yet.</p>}
              </div>
            </GlassCard>
          </div>

          <GlassCard className="p-3">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-foreground">Selected file</p>
                <p className="mt-1 break-all text-[10px] text-muted-foreground">
                  {selectedDocument?.relative_path || 'Choose a file from the list above.'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {selectedDocument ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-[10px]"
                    onClick={handleOpenRemote}
                  >
                    <ExternalLink className="mr-1 h-3 w-3" />
                    Open remote
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  className="h-8 text-[10px]"
                  disabled={!selectedDocument || importMutation.isPending}
                  onClick={() => selectedDocument && importMutation.mutate(selectedDocument)}
                >
                  {importMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Import className="mr-1 h-3.5 w-3.5" />}
                  Import into Document Library
                </Button>
              </div>
            </div>
          </GlassCard>
        </div>
      </SheetContent>
    </Sheet>
  );
}

import { useQuery } from '@tanstack/react-query';
import { Search, Command, Settings, Activity, Zap } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { useLocation } from 'react-router-dom';
import { AI_LAB_ROUTE_MAP } from '@/lib/ai-lab-navigation';
import { getRuntimeControls } from '@/lib/product-api';
import { getRuntimeConnection } from '@/lib/runtime-controls-ui';

const routeTitles: Record<string, string> = {
  '/app': 'Command Center',
  '/app/documents': 'Document Library',
  '/app/workflows': 'Workflows',
  '/app/workflows/document-review': 'Document Review',
  '/app/workflows/comparison': 'Policy Comparison',
  '/app/workflows/action-plan': 'Action Plan',
  '/app/workflows/candidate-review': 'Candidate Review',
  '/app/deck-center': 'Deck Center',
  '/app/history': 'Run History',
  '/app/settings/runtime': 'Runtime Controls',
  '/app/settings/preferences': 'Preferences',
};

export default function TopBar() {
  const { setCommandPaletteOpen, setRuntimeDrawerOpen } = useAppStore();
  const location = useLocation();
  const { data: runtimeControls, isLoading: runtimeControlsLoading, isError: runtimeControlsError } = useQuery({
    queryKey: ['runtime-controls'],
    queryFn: getRuntimeControls,
    refetchOnWindowFocus: false,
  });
  const labRoute = AI_LAB_ROUTE_MAP[location.pathname];
  const productTitle = routeTitles[location.pathname];
  const title = labRoute?.label || productTitle || 'AI Decision Studio';
  const isLab = !!labRoute;
  const isSystem = !isLab && location.pathname.startsWith('/app/settings/');
  const isProduct = !isLab && !isSystem && !!productTitle;
  const sectionBadge = isLab ? 'AI Lab' : isSystem ? 'System' : isProduct ? 'Product' : null;
  const activeProfile = runtimeControls?.active_profile;
  const primaryConnection = activeProfile ? getRuntimeConnection(runtimeControls, activeProfile.primaryConnectionId) : undefined;
  const runtimeLabel = runtimeControlsLoading
    ? 'Loading runtime…'
    : runtimeControlsError || !activeProfile
      ? 'Runtime unavailable'
      : `${primaryConnection?.name ?? activeProfile.primaryConnectionId} · ${activeProfile.primaryModel}`;

  return (
    <header className="h-14 border-b border-border/50 flex items-center justify-between px-6 bg-background/80 backdrop-blur-md sticky top-0 z-20">
      <div className="flex items-center gap-4">
        {sectionBadge && (
          <span className="text-[9px] uppercase tracking-widest text-primary/60 font-medium">
            {sectionBadge}
          </span>
        )}
        <h2 className="text-sm font-medium text-foreground">{title}</h2>
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-muted-foreground bg-secondary/50 px-2 py-1 rounded-md">
          <Activity className="w-3 h-3 text-glow-success" />
          <span>{runtimeLabel}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border/50 bg-secondary/30 text-muted-foreground hover:text-foreground hover:bg-secondary/50 text-xs transition-colors">
          <Search className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Search or command...</span>
          <kbd className="hidden md:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-background rounded text-[10px] border border-border/50">
            <Command className="w-2.5 h-2.5" /> K
          </kbd>
        </button>
        <button onClick={() => setRuntimeDrawerOpen(true)}
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors">
          <Settings className="w-4 h-4" />
        </button>
        <button className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors">
          <Zap className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}

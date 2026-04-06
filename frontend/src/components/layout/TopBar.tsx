import { Search, Command, Settings, Activity, Zap } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { useLocation } from 'react-router-dom';

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
  '/app/lab/chat': 'Chat with RAG',
  '/app/lab/structured': 'Structured Outputs',
  '/app/lab/models': 'Model Comparison',
  '/app/lab/evidenceops': 'EvidenceOps MCP',
  '/app/settings/runtime': 'Runtime Controls',
  '/app/settings/preferences': 'Preferences',
};

export default function TopBar() {
  const { setCommandPaletteOpen, setRuntimeDrawerOpen } = useAppStore();
  const location = useLocation();
  const title = routeTitles[location.pathname] || 'AI Decision Studio';

  return (
    <header className="h-14 border-b border-border/50 flex items-center justify-between px-6 bg-background/80 backdrop-blur-md sticky top-0 z-20">
      <div className="flex items-center gap-4">
        <h2 className="text-sm font-medium text-foreground">{title}</h2>
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-muted-foreground bg-secondary/50 px-2 py-1 rounded-md">
          <Activity className="w-3 h-3 text-glow-success" />
          <span>ollama · qwen2.5:32b</span>
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

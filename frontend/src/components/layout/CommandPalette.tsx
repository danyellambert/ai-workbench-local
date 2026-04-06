import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/lib/store';
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from '@/components/ui/command';
import {
  LayoutDashboard, FileText, Workflow, FileOutput, MessageSquare,
  Layers, BarChart3, Terminal, Settings, Shield, GitCompare,
  ClipboardList, UserCheck, Zap, Play
} from 'lucide-react';

const commands = [
  { group: 'Navigate', items: [
    { label: 'Command Center', path: '/app', icon: LayoutDashboard },
    { label: 'Document Library', path: '/app/documents', icon: FileText },
    { label: 'Document Review', path: '/app/workflows/document-review', icon: Shield },
    { label: 'Policy Comparison', path: '/app/workflows/comparison', icon: GitCompare },
    { label: 'Action Plan', path: '/app/workflows/action-plan', icon: ClipboardList },
    { label: 'Candidate Review', path: '/app/workflows/candidate-review', icon: UserCheck },
    { label: 'Deck Center', path: '/app/deck-center', icon: FileOutput },
    { label: 'Chat with RAG', path: '/app/lab/chat', icon: MessageSquare },
    { label: 'Structured Outputs', path: '/app/lab/structured', icon: Layers },
    { label: 'Model Comparison', path: '/app/lab/models', icon: BarChart3 },
    { label: 'EvidenceOps MCP', path: '/app/lab/evidenceops', icon: Terminal },
  ]},
  { group: 'Quick Actions', items: [
    { label: 'Run Document Risk Review', path: '/app/workflows/document-review', icon: Play },
    { label: 'Compare Contract Versions', path: '/app/workflows/comparison', icon: GitCompare },
    { label: 'Build Action Plan', path: '/app/workflows/action-plan', icon: ClipboardList },
    { label: 'Review Candidate CV', path: '/app/workflows/candidate-review', icon: UserCheck },
    { label: 'Open Runtime Controls', path: '/app/settings/runtime', icon: Settings },
  ]},
];

export default function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen } = useAppStore();
  const navigate = useNavigate();

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      setCommandPaletteOpen(true);
    }
  }, [setCommandPaletteOpen]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleSelect = (path: string) => {
    navigate(path);
    setCommandPaletteOpen(false);
  };

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <CommandInput placeholder="Search pages, workflows, actions..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {commands.map((group, i) => (
          <div key={group.group}>
            {i > 0 && <CommandSeparator />}
            <CommandGroup heading={group.group}>
              {group.items.map(item => (
                <CommandItem key={item.label} onSelect={() => handleSelect(item.path)} className="gap-3 cursor-pointer">
                  <item.icon className="w-4 h-4 text-muted-foreground" />
                  <span>{item.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </div>
        ))}
      </CommandList>
    </CommandDialog>
  );
}

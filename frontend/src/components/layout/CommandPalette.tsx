import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/lib/store';
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from '@/components/ui/command';
import {
  LayoutDashboard, FileText, Workflow, FileOutput,
  Settings, Shield, GitCompare, ClipboardList, UserCheck, Play,
} from 'lucide-react';
import { AI_LAB_ROUTES } from '@/lib/ai-lab-navigation';

const commands = [
  {
    group: 'Product',
    items: [
      { label: 'Command Center', path: '/app', icon: LayoutDashboard },
      { label: 'Document Library', path: '/app/documents', icon: FileText },
      { label: 'Document Review', path: '/app/workflows/document-review', icon: Shield },
      { label: 'Policy Comparison', path: '/app/workflows/comparison', icon: GitCompare },
      { label: 'Action Plan', path: '/app/workflows/action-plan', icon: ClipboardList },
      { label: 'Candidate Review', path: '/app/workflows/candidate-review', icon: UserCheck },
      { label: 'Deck Center', path: '/app/deck-center', icon: FileOutput },
    ],
  },
  {
    group: 'AI Lab',
    items: AI_LAB_ROUTES.map((route) => ({ label: route.label, path: route.path, icon: route.icon })),
  },
  {
    group: 'Quick Actions',
    items: [
      { label: 'Run Document Risk Review', path: '/app/workflows/document-review', icon: Play },
      { label: 'Compare Contract Versions', path: '/app/workflows/comparison', icon: GitCompare },
      { label: 'Open Runtime Controls', path: '/app/settings/runtime', icon: Settings },
    ],
  },
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
      <CommandInput placeholder="Search pages, workflows, AI Lab..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {commands.map((group, i) => (
          <div key={group.group}>
            {i > 0 && <CommandSeparator />}
            <CommandGroup heading={group.group}>
              {group.items.map(item => (
                <CommandItem key={item.label + item.path} onSelect={() => handleSelect(item.path)} className="gap-3 cursor-pointer">
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

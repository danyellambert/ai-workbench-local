import { useLocation, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, FileText, Workflow, FileOutput, History,
  MessageSquare, Layers, BarChart3, Terminal,
  Settings, Palette, Server, ChevronLeft, ChevronRight,
  Sparkles, Shield, GitCompare, ClipboardList, UserCheck
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

const productNav = [
  { label: 'Command Center', path: '/app', icon: LayoutDashboard },
  { label: 'Document Library', path: '/app/documents', icon: FileText },
  { label: 'Workflows', path: '/app/workflows', icon: Workflow, children: [
    { label: 'Document Review', path: '/app/workflows/document-review', icon: Shield },
    { label: 'Policy Comparison', path: '/app/workflows/comparison', icon: GitCompare },
    { label: 'Action Plan', path: '/app/workflows/action-plan', icon: ClipboardList },
    { label: 'Candidate Review', path: '/app/workflows/candidate-review', icon: UserCheck },
  ]},
  { label: 'Deck Center', path: '/app/deck-center', icon: FileOutput },
  { label: 'Run History', path: '/app/history', icon: History },
];

const labNav = [
  { label: 'Chat with RAG', path: '/app/lab/chat', icon: MessageSquare },
  { label: 'Structured Outputs', path: '/app/lab/structured', icon: Layers },
  { label: 'Model Comparison', path: '/app/lab/models', icon: BarChart3 },
  { label: 'EvidenceOps MCP', path: '/app/lab/evidenceops', icon: Terminal },
];

const systemNav = [
  { label: 'Runtime Controls', path: '/app/settings/runtime', icon: Server },
  { label: 'Preferences', path: '/app/settings/preferences', icon: Palette },
];

interface NavItemProps {
  item: { label: string; path: string; icon: React.ElementType; children?: { label: string; path: string; icon: React.ElementType }[] };
  collapsed: boolean;
  currentPath: string;
}

function NavItem({ item, collapsed, currentPath }: NavItemProps) {
  const isActive = currentPath === item.path || item.children?.some(c => currentPath === c.path);
  const Icon = item.icon;

  return (
    <div>
      <Link to={item.children ? item.children[0].path : item.path}
        className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200 group relative",
          isActive
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
        )}>
        {isActive && (
          <motion.div layoutId="sidebar-active" className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary" />
        )}
        <Icon className="w-4 h-4 shrink-0" />
        {!collapsed && <span className="truncate">{item.label}</span>}
      </Link>
      {!collapsed && item.children && isActive && (
        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="ml-7 mt-1 space-y-0.5 overflow-hidden">
          {item.children.map(child => (
            <Link key={child.path} to={child.path}
              className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md text-xs transition-colors",
                currentPath === child.path ? "text-primary bg-primary/5" : "text-muted-foreground hover:text-foreground"
              )}>
              <child.icon className="w-3.5 h-3.5" />
              <span>{child.label}</span>
            </Link>
          ))}
        </motion.div>
      )}
    </div>
  );
}

export default function AppSidebar() {
  const { sidebarOpen, toggleSidebar } = useAppStore();
  const location = useLocation();
  const collapsed = !sidebarOpen;

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 256 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="h-screen sticky top-0 flex flex-col bg-sidebar border-r border-sidebar-border z-30 overflow-hidden"
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-sidebar-border shrink-0">
        <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center shrink-0">
          <Sparkles className="w-4 h-4 text-primary" />
        </div>
        {!collapsed && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-w-0">
            <h1 className="text-sm font-semibold text-foreground truncate">AI Decision Studio</h1>
            <p className="text-[10px] text-muted-foreground">Local · v2.4</p>
            <p className="text-[10px] text-primary/80 truncate">Built by Danyel Lambert</p>
          </motion.div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6 scrollbar-thin">
        <div>
          {!collapsed && <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60 px-3 mb-2 font-medium">Product</p>}
          <nav className="space-y-0.5">
            {productNav.map(item => <NavItem key={item.path} item={item} collapsed={collapsed} currentPath={location.pathname} />)}
          </nav>
        </div>
        <div>
          {!collapsed && <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60 px-3 mb-2 font-medium">AI Lab</p>}
          <nav className="space-y-0.5">
            {labNav.map(item => <NavItem key={item.path} item={item} collapsed={collapsed} currentPath={location.pathname} />)}
          </nav>
        </div>
        <div>
          {!collapsed && <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60 px-3 mb-2 font-medium">System</p>}
          <nav className="space-y-0.5">
            {systemNav.map(item => <NavItem key={item.path} item={item} collapsed={collapsed} currentPath={location.pathname} />)}
          </nav>
        </div>
      </div>

      {/* Toggle */}
      <button onClick={toggleSidebar}
        className="h-10 flex items-center justify-center border-t border-sidebar-border text-muted-foreground hover:text-foreground transition-colors">
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </motion.aside>
  );
}

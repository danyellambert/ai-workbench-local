import { useEffect, useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, FileText, Workflow, FileOutput, History,
  Palette, Server, ChevronLeft, ChevronRight,
  Sparkles, Shield, GitCompare, ClipboardList, UserCheck,
  LayoutGrid, MessageSquare, BarChart3, ShieldCheck, Archive, Terminal,
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import { AI_LAB_ROUTES } from '@/lib/ai-lab-navigation';
import { APP_CONFIG } from '@/lib/app-config';
import KeystoneLogo from '@/components/KeystoneLogo';
import MeetDanyelModal from '@/components/landing/MeetDanyelModal';

const productNav = [
  { label: 'Command Center', path: '/app', icon: LayoutDashboard, tourId: 'nav-command-center' },
  { label: 'Document Library', path: '/app/documents', icon: FileText, tourId: 'nav-documents' },
  { label: 'Workflows', path: '/app/workflows', icon: Workflow, tourId: 'nav-workflows', children: [
    { label: 'Document Review', path: '/app/workflows/document-review', icon: Shield },
    { label: 'Policy Comparison', path: '/app/workflows/comparison', icon: GitCompare },
    { label: 'Action Plan', path: '/app/workflows/action-plan', icon: ClipboardList },
    { label: 'Candidate Review', path: '/app/workflows/candidate-review', icon: UserCheck },
  ]},
  { label: 'Deck Center', path: '/app/deck-center', icon: FileOutput, tourId: 'nav-deck-center' },
  { label: 'Run History', path: '/app/history', icon: History, tourId: 'nav-history' },
];

const labNav = AI_LAB_ROUTES.map((route) => ({ label: route.label, path: route.path, icon: route.icon, tourId: `nav-lab-${route.key}` }));

const systemNav = [
  { label: 'Runtime Controls', path: '/app/settings/runtime', icon: Server, tourId: 'nav-runtime-controls' },
  { label: 'Preferences', path: '/app/settings/preferences', icon: Palette, tourId: 'nav-preferences' },
];

interface NavItemProps {
  item: { label: string; path: string; icon: React.ElementType; tourId?: string; children?: { label: string; path: string; icon: React.ElementType }[] };
  collapsed: boolean;
  currentPath: string;
}

type WorkflowTourCueRect = { top: number; left: number; height: number; width: number };
type TourShortcutKind = 'workflow' | 'document-review' | 'policy-comparison' | 'action-plan' | 'candidate-review' | 'deck-center' | 'run-history' | 'runtime-controls' | 'preferences' | 'lab-overview' | 'lab-runtime' | 'lab-document-experiments' | 'lab-workflow-inspector' | 'lab-benchmarks' | 'lab-evals' | 'lab-artifacts' | 'lab-evidenceops';

function NavItem({ item, collapsed, currentPath }: NavItemProps) {
  const isActive = currentPath === item.path || item.children?.some(c => currentPath === c.path);
  const Icon = item.icon;

  return (
    <div className="relative">
      <Link to={item.children ? item.children[0].path : item.path}
        data-tour={item.tourId}
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
  const navigate = useNavigate();
  const collapsed = !sidebarOpen;
  const [workflowCueRect, setWorkflowCueRect] = useState<WorkflowTourCueRect | null>(null);
  const [showWorkflowTourPrompt, setShowWorkflowTourPrompt] = useState(false);
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [tourShortcutKind, setTourShortcutKind] = useState<TourShortcutKind | null>(() => {
    try {
      if (window.localStorage.getItem('workbench-tour-lab-artifacts-complete') === '1') return 'lab-evidenceops';
      if (window.localStorage.getItem('workbench-tour-lab-evals-complete') === '1') return 'lab-artifacts';
      if (window.localStorage.getItem('workbench-tour-lab-benchmarks-complete') === '1') return 'lab-evals';
      if (window.localStorage.getItem('workbench-tour-lab-workflow-inspector-complete') === '1') return 'lab-benchmarks';
      if (window.localStorage.getItem('workbench-tour-lab-document-experiments-complete') === '1') return 'lab-workflow-inspector';
      if (window.localStorage.getItem('workbench-tour-lab-runtime-complete') === '1') return 'lab-document-experiments';
      if (window.localStorage.getItem('workbench-tour-lab-overview-complete') === '1') return 'lab-runtime';
      if (window.localStorage.getItem('workbench-tour-preferences-complete') === '1') return 'lab-overview';
      if (window.localStorage.getItem('workbench-tour-runtime-controls-complete') === '1') return 'preferences';
      if (window.localStorage.getItem('workbench-tour-run-history-complete') === '1') return 'runtime-controls';
      if (window.localStorage.getItem('workbench-tour-deck-center-complete') === '1') return 'run-history';
      if (window.localStorage.getItem('workbench-tour-candidate-review-complete') === '1') return 'deck-center';
      if (window.localStorage.getItem('workbench-tour-action-plan-complete') === '1') return 'candidate-review';
      if (window.localStorage.getItem('workbench-tour-policy-comparison-complete') === '1') return 'action-plan';
      if (window.localStorage.getItem('workbench-tour-document-review-complete') === '1') return 'policy-comparison';
      if (window.localStorage.getItem('workbench-tour-workflow-complete') === '1') return 'document-review';
      if (window.localStorage.getItem('workbench-tour-document-library-complete') === '1') return 'workflow';
      return null;
    } catch {
      return null;
    }
  });

  const clearTourShortcut = (kind: TourShortcutKind | null = tourShortcutKind) => {
    try {
      if (kind === 'lab-evidenceops') {
        window.localStorage.removeItem('workbench-tour-lab-artifacts-complete');
      } else if (kind === 'lab-artifacts') {
        window.localStorage.removeItem('workbench-tour-lab-evals-complete');
      } else if (kind === 'lab-evals') {
        window.localStorage.removeItem('workbench-tour-lab-benchmarks-complete');
      } else if (kind === 'lab-benchmarks') {
        window.localStorage.removeItem('workbench-tour-lab-workflow-inspector-complete');
      } else if (kind === 'lab-workflow-inspector') {
        window.localStorage.removeItem('workbench-tour-lab-document-experiments-complete');
      } else if (kind === 'lab-document-experiments') {
        window.localStorage.removeItem('workbench-tour-lab-runtime-complete');
      } else if (kind === 'lab-runtime') {
        window.localStorage.removeItem('workbench-tour-lab-overview-complete');
      } else if (kind === 'lab-overview') {
        window.localStorage.removeItem('workbench-tour-preferences-complete');
      } else if (kind === 'preferences') {
        window.localStorage.removeItem('workbench-tour-runtime-controls-complete');
      } else if (kind === 'runtime-controls') {
        window.localStorage.removeItem('workbench-tour-run-history-complete');
      } else if (kind === 'run-history') {
        window.localStorage.removeItem('workbench-tour-deck-center-complete');
      } else if (kind === 'deck-center') {
        window.localStorage.removeItem('workbench-tour-candidate-review-complete');
      } else if (kind === 'candidate-review') {
        window.localStorage.removeItem('workbench-tour-action-plan-complete');
      } else if (kind === 'action-plan') {
        window.localStorage.removeItem('workbench-tour-policy-comparison-complete');
      } else if (kind === 'policy-comparison') {
        window.localStorage.removeItem('workbench-tour-document-review-complete');
      } else if (kind === 'document-review') {
        window.localStorage.removeItem('workbench-tour-workflow-complete');
      } else if (kind === 'workflow') {
        window.localStorage.removeItem('workbench-tour-document-library-complete');
      }
    } catch {
      // Ignore storage failures; the visual cue can still disappear for this session.
    }
    setTourShortcutKind(null);
    setShowWorkflowTourPrompt(false);
  };

  const startNextTour = () => {
    const nextKind = tourShortcutKind || 'workflow';
    clearTourShortcut(nextKind);
    navigate(
      nextKind === 'lab-evidenceops'
        ? '/app/lab/evidenceops?tour=lab-evidenceops'
        : nextKind === 'lab-artifacts'
          ? '/app/lab/artifacts?tour=lab-artifacts'
          : nextKind === 'lab-evals'
            ? '/app/lab/evals?tour=lab-evals'
            : nextKind === 'lab-benchmarks'
              ? '/app/lab/benchmarks?tour=lab-benchmarks'
              : nextKind === 'lab-workflow-inspector'
                ? '/app/lab/workflow-inspector?tour=lab-workflow-inspector'
        : nextKind === 'lab-document-experiments'
          ? '/app/lab/chat?tour=lab-document-experiments'
          : nextKind === 'lab-runtime'
            ? '/app/lab/runtime?tour=lab-runtime'
            : nextKind === 'lab-overview'
              ? '/app/lab/overview?tour=lab-overview'
              : nextKind === 'preferences'
                ? '/app/settings/preferences?tour=preferences'
                : nextKind === 'runtime-controls'
          ? '/app/settings/runtime?tour=runtime-controls'
          : nextKind === 'run-history'
            ? '/app/history?tour=run-history'
            : nextKind === 'deck-center'
              ? '/app/deck-center?tour=deck-center'
              : nextKind === 'candidate-review'
                ? '/app/workflows/candidate-review?tour=candidate-review'
                : nextKind === 'action-plan'
                  ? '/app/workflows/action-plan?tour=action-plan'
                  : nextKind === 'policy-comparison'
                    ? '/app/workflows/comparison?tour=policy-comparison'
                    : nextKind === 'document-review'
                      ? '/app/workflows/document-review?tour=document-review'
                      : '/app/workflows?tour=workflow',
    );
  };

  const dismissWorkflowTourPrompt = () => {
    setShowWorkflowTourPrompt(false);
  };

  const nextTourCopy = tourShortcutKind === 'lab-evidenceops'
    ? {
        title: 'Ready to finish with MCP Operations?',
        body: 'This final AI Lab tour explains operations and governance: MCP tools, backlog actions, delivery targets, telemetry, readiness, and repository search.',
        cta: 'Start MCP Operations tour',
      }
    : tourShortcutKind === 'lab-artifacts'
      ? {
          title: 'Ready to continue into Experiments & Artifacts?',
          body: 'This AI Lab section shows persisted evidence: export bundles, run registry, captures, processing diagnostics, and artifact explorer.',
          cta: 'Start artifacts tour',
        }
      : tourShortcutKind === 'lab-evals'
        ? {
            title: 'Ready to continue into Evals & Diagnosis?',
            body: 'This AI Lab section explains quality control: historical baseline, live telemetry, regressions, investigation queue, and recent eval cases.',
            cta: 'Start evals tour',
          }
        : tourShortcutKind === 'lab-benchmarks'
          ? {
              title: 'Ready to continue into Benchmarks?',
              body: 'This AI Lab section compares models and retrieval strategies using recorded benchmark evidence, fit, groundedness, adherence, and latency.',
              cta: 'Start benchmarks tour',
            }
          : tourShortcutKind === 'lab-workflow-inspector'
    ? {
        title: 'Ready to finish with Workflow Inspector?',
        body: 'This final AI Lab tour shows the trace-level audit view: controls, run output, case history, and latest execution evidence.',
        cta: 'Start inspector tour',
      }
    : tourShortcutKind === 'lab-document-experiments'
      ? {
          title: 'Ready to continue into Document Experiments?',
          body: 'This AI Lab section is for probing grounded chat behavior, selected documents, and RAG quality outside the product workflow.',
          cta: 'Start experiments tour',
        }
      : tourShortcutKind === 'lab-runtime'
        ? {
            title: 'Ready to continue into Runtime & Observability?',
            body: 'This AI Lab section is the technical runtime view: provider health, retrieval behavior, latency, cost, and trace signals.',
            cta: 'Start runtime lab tour',
          }
        : tourShortcutKind === 'lab-overview'
          ? {
              title: 'Ready to open the technical AI Lab layer?',
              body: 'The product tour is finished. Continue here only when you want to explain what is behind the product: observability, diagnostics, experiments, and auditability.',
              cta: 'Start AI Lab tour',
            }
          : tourShortcutKind === 'preferences'
            ? {
                title: 'Ready to continue into Preferences?',
                body: 'You can start the final product configuration pass now, or skip it and keep exploring Runtime Controls.',
                cta: 'Start preferences tour',
              }
            : tourShortcutKind === 'runtime-controls'
      ? {
          title: 'Ready to continue into Runtime Controls?',
          body: 'You can start the Runtime Controls tour now, or skip it and keep exploring Run History.',
          cta: 'Start runtime tour',
        }
      : tourShortcutKind === 'run-history'
        ? {
            title: 'Ready to continue into Run History?',
            body: 'You can start the Run History tour now, or skip it and keep exploring Deck Center.',
            cta: 'Start history tour',
          }
        : tourShortcutKind === 'deck-center'
          ? {
              title: 'Ready to continue into Deck Center?',
              body: 'You can start the Deck Center tour now, or skip it and keep exploring Candidate Review.',
              cta: 'Start deck tour',
            }
          : tourShortcutKind === 'candidate-review'
            ? {
                title: 'Ready to continue into Candidate Review?',
                body: 'You can start the Candidate Review tour now, or skip it and keep exploring Action Plan.',
                cta: 'Start candidate tour',
              }
            : tourShortcutKind === 'action-plan'
              ? {
                  title: 'Ready to continue into Action Plan?',
                  body: 'You can start the Action Plan tour now, or skip it and keep exploring the Policy Comparison workflow.',
                  cta: 'Start action plan tour',
                }
              : tourShortcutKind === 'policy-comparison'
                ? {
                    title: 'Ready to continue into Policy Comparison?',
                    body: 'You can start the Policy Comparison tour now, or skip it and keep exploring Document Review.',
                    cta: 'Start policy tour',
                  }
                : tourShortcutKind === 'document-review'
                  ? {
                      title: 'Ready to start Document Review?',
                      body: 'You can start the Document Review tour now, or skip it and keep exploring the workflow catalog.',
                      cta: 'Start document review',
                    }
                  : {
                      title: 'Ready to continue into Workflows?',
                      body: 'You can start the workflow tour now, or skip it and keep exploring the Document Library.',
                      cta: 'Start workflow tour',
                    };

  useEffect(() => {
    const syncShortcut = () => {
      try {
        if (window.localStorage.getItem('workbench-tour-lab-artifacts-complete') === '1') {
          setTourShortcutKind('lab-evidenceops');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-lab-evals-complete') === '1') {
          setTourShortcutKind('lab-artifacts');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-lab-benchmarks-complete') === '1') {
          setTourShortcutKind('lab-evals');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-lab-workflow-inspector-complete') === '1') {
          setTourShortcutKind('lab-benchmarks');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-lab-document-experiments-complete') === '1') {
          setTourShortcutKind('lab-workflow-inspector');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-lab-runtime-complete') === '1') {
          setTourShortcutKind('lab-document-experiments');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-lab-overview-complete') === '1') {
          setTourShortcutKind('lab-runtime');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-preferences-complete') === '1') {
          setTourShortcutKind('lab-overview');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-runtime-controls-complete') === '1') {
          setTourShortcutKind('preferences');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-run-history-complete') === '1') {
          setTourShortcutKind('runtime-controls');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-deck-center-complete') === '1') {
          setTourShortcutKind('run-history');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-candidate-review-complete') === '1') {
          setTourShortcutKind('deck-center');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-action-plan-complete') === '1') {
          setTourShortcutKind('candidate-review');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-policy-comparison-complete') === '1') {
          setTourShortcutKind('action-plan');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-document-review-complete') === '1') {
          setTourShortcutKind('policy-comparison');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-workflow-complete') === '1') {
          setTourShortcutKind('document-review');
          return;
        }
        if (window.localStorage.getItem('workbench-tour-document-library-complete') === '1') {
          setTourShortcutKind('workflow');
          return;
        }
        setTourShortcutKind(null);
      } catch {
        setTourShortcutKind(null);
      }
    };
    const openPrompt = () => {
      syncShortcut();
      setShowWorkflowTourPrompt(true);
    };
    window.addEventListener('workbench-tour:document-library-complete', syncShortcut);
    window.addEventListener('workbench-tour:workflow-complete', syncShortcut);
    window.addEventListener('workbench-tour:document-review-complete', syncShortcut);
    window.addEventListener('workbench-tour:policy-comparison-complete', syncShortcut);
    window.addEventListener('workbench-tour:action-plan-complete', syncShortcut);
    window.addEventListener('workbench-tour:candidate-review-complete', syncShortcut);
    window.addEventListener('workbench-tour:deck-center-complete', syncShortcut);
    window.addEventListener('workbench-tour:run-history-complete', syncShortcut);
    window.addEventListener('workbench-tour:runtime-controls-complete', syncShortcut);
    window.addEventListener('workbench-tour:preferences-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-overview-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-runtime-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-document-experiments-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-workflow-inspector-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-benchmarks-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-evals-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-artifacts-complete', syncShortcut);
    window.addEventListener('workbench-tour:lab-evidenceops-complete', syncShortcut);
    window.addEventListener('workbench-tour:ready-for-workflow-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-document-review-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-policy-comparison-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-action-plan-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-candidate-review-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-deck-center-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-run-history-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-runtime-controls-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-preferences-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-overview-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-runtime-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-document-experiments-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-workflow-inspector-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-benchmarks-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-evals-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-artifacts-tour', openPrompt);
    window.addEventListener('workbench-tour:ready-for-lab-evidenceops-tour', openPrompt);
    window.addEventListener('storage', syncShortcut);
    return () => {
      window.removeEventListener('workbench-tour:document-library-complete', syncShortcut);
      window.removeEventListener('workbench-tour:workflow-complete', syncShortcut);
      window.removeEventListener('workbench-tour:document-review-complete', syncShortcut);
      window.removeEventListener('workbench-tour:policy-comparison-complete', syncShortcut);
      window.removeEventListener('workbench-tour:action-plan-complete', syncShortcut);
      window.removeEventListener('workbench-tour:candidate-review-complete', syncShortcut);
      window.removeEventListener('workbench-tour:deck-center-complete', syncShortcut);
      window.removeEventListener('workbench-tour:run-history-complete', syncShortcut);
      window.removeEventListener('workbench-tour:runtime-controls-complete', syncShortcut);
      window.removeEventListener('workbench-tour:preferences-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-overview-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-runtime-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-document-experiments-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-workflow-inspector-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-benchmarks-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-evals-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-artifacts-complete', syncShortcut);
      window.removeEventListener('workbench-tour:lab-evidenceops-complete', syncShortcut);
      window.removeEventListener('workbench-tour:ready-for-workflow-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-document-review-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-policy-comparison-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-action-plan-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-candidate-review-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-deck-center-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-run-history-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-runtime-controls-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-preferences-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-overview-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-runtime-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-document-experiments-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-workflow-inspector-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-benchmarks-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-evals-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-artifacts-tour', openPrompt);
      window.removeEventListener('workbench-tour:ready-for-lab-evidenceops-tour', openPrompt);
      window.removeEventListener('storage', syncShortcut);
    };
  }, []);

  useEffect(() => {
    const measureWorkflowCue = () => {
      const targetSelector = tourShortcutKind === 'lab-evidenceops'
        ? '[data-tour="nav-lab-evidenceops"]'
        : tourShortcutKind === 'lab-artifacts'
          ? '[data-tour="nav-lab-artifacts"]'
          : tourShortcutKind === 'lab-evals'
            ? '[data-tour="nav-lab-evals"]'
            : tourShortcutKind === 'lab-benchmarks'
              ? '[data-tour="nav-lab-benchmarks"]'
              : tourShortcutKind === 'lab-workflow-inspector'
                ? '[data-tour="nav-lab-workflow-inspector"]'
        : tourShortcutKind === 'lab-document-experiments'
          ? '[data-tour="nav-lab-chat"]'
          : tourShortcutKind === 'lab-runtime'
            ? '[data-tour="nav-lab-runtime"]'
            : tourShortcutKind === 'lab-overview'
              ? '[data-tour="nav-lab-overview"]'
              : tourShortcutKind === 'preferences'
                ? '[data-tour="nav-preferences"]'
                : tourShortcutKind === 'runtime-controls'
                  ? '[data-tour="nav-runtime-controls"]'
                  : tourShortcutKind === 'run-history'
                    ? '[data-tour="nav-history"]'
                    : tourShortcutKind === 'deck-center'
                      ? '[data-tour="nav-deck-center"]'
                      : '[data-tour="nav-workflows"]';
      const target = document.querySelector(targetSelector) as HTMLElement | null;
      if (!target || collapsed) {
        setWorkflowCueRect(null);
        return;
      }
      const rect = target.getBoundingClientRect();
      setWorkflowCueRect({ top: rect.top, left: rect.left, width: rect.width, height: rect.height });
    };
    measureWorkflowCue();
    window.addEventListener('resize', measureWorkflowCue);
    window.addEventListener('scroll', measureWorkflowCue, true);
    const id = window.setInterval(measureWorkflowCue, 450);
    return () => {
      window.removeEventListener('resize', measureWorkflowCue);
      window.removeEventListener('scroll', measureWorkflowCue, true);
      window.clearInterval(id);
    };
  }, [collapsed, location.pathname, tourShortcutKind]);

  const shortcutLabel = tourShortcutKind === 'lab-evidenceops'
    ? 'MCP Operations'
    : tourShortcutKind === 'lab-artifacts'
      ? 'Experiments & Artifacts'
      : tourShortcutKind === 'lab-evals'
        ? 'Evals & Diagnosis'
        : tourShortcutKind === 'lab-benchmarks'
          ? 'Benchmarks'
          : tourShortcutKind === 'lab-workflow-inspector'
    ? 'Workflow Inspector'
    : tourShortcutKind === 'lab-document-experiments'
      ? 'Document Experiments'
      : tourShortcutKind === 'lab-runtime'
        ? 'Runtime & Observability'
        : tourShortcutKind === 'lab-overview'
          ? 'Overview'
          : tourShortcutKind === 'deck-center'
            ? 'Deck Center'
            : tourShortcutKind === 'run-history'
              ? 'Run History'
              : tourShortcutKind === 'runtime-controls'
                ? 'Runtime Controls'
                : tourShortcutKind === 'preferences'
                  ? 'Preferences'
                  : 'Workflows';
  const ShortcutIcon = tourShortcutKind === 'lab-evidenceops'
    ? Terminal
    : tourShortcutKind === 'lab-artifacts'
      ? Archive
      : tourShortcutKind === 'lab-evals'
        ? ShieldCheck
        : tourShortcutKind === 'lab-benchmarks'
          ? BarChart3
          : tourShortcutKind === 'lab-workflow-inspector'
    ? Workflow
    : tourShortcutKind === 'lab-document-experiments'
      ? MessageSquare
      : tourShortcutKind === 'lab-runtime'
        ? Server
        : tourShortcutKind === 'lab-overview'
          ? LayoutGrid
          : tourShortcutKind === 'deck-center'
            ? FileOutput
            : tourShortcutKind === 'run-history'
              ? History
              : tourShortcutKind === 'runtime-controls'
                ? Server
                : tourShortcutKind === 'preferences'
                  ? Palette
                  : Workflow;

  return (
    <>
    <motion.aside
      animate={{ width: collapsed ? 64 : 256 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="h-screen sticky top-0 flex flex-col bg-sidebar border-r border-sidebar-border z-30 overflow-hidden"
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-sidebar-border shrink-0">
        <Link
          to="/"
          aria-label="Open landing page"
          className="rounded-lg transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary/60 focus:ring-offset-2 focus:ring-offset-sidebar"
        >
          <KeystoneLogo size={32} />
        </Link>
        {!collapsed && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-w-0">
            <h1 className="text-sm font-semibold text-foreground truncate">{APP_CONFIG.name}</h1>
            <button
              type="button"
              onClick={() => setIsBuilderOpen(true)}
              className="block text-left text-[10px] text-muted-foreground transition-colors hover:text-primary focus:outline-none focus:text-primary"
              aria-label="Open Meet Danyel card"
              data-usage-label="by Danyel Lambert"
            >
              by Danyel Lambert
            </button>
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


      {tourShortcutKind && workflowCueRect && (
        <>
          {showWorkflowTourPrompt && (
            <>
              <div className="fixed inset-0 z-[65] bg-background/45 backdrop-blur-[1px]" />
              <motion.div
                className="fixed z-[69] rounded-xl border border-primary/70 bg-transparent shadow-[0_0_0_9999px_rgba(0,0,0,0.35),0_0_34px_-10px_hsl(var(--primary))]"
                style={{
                  left: workflowCueRect.left - 4,
                  top: workflowCueRect.top - 4,
                  width: workflowCueRect.width + 8,
                  height: workflowCueRect.height + 8,
                }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              />
            </>
          )}
          {showWorkflowTourPrompt && (
            <motion.div
              className="fixed z-[70] pointer-events-none flex items-center gap-3 rounded-lg bg-primary/10 px-3 py-2 text-sm text-primary shadow-lg shadow-primary/20 backdrop-blur-md"
              style={{
                left: workflowCueRect.left,
                top: workflowCueRect.top,
                width: workflowCueRect.width,
                height: workflowCueRect.height,
              }}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <ShortcutIcon className="h-4 w-4 shrink-0" />
              <span className="truncate">{shortcutLabel}</span>
            </motion.div>
          )}
          <motion.div
            className={cn("fixed pointer-events-auto", showWorkflowTourPrompt ? "z-[72]" : "z-[70]")}
            style={{
              left: Math.max(workflowCueRect.left + 44, workflowCueRect.left + workflowCueRect.width - 112),
              top: workflowCueRect.top + Math.max(6, workflowCueRect.height / 2 - 12),
            }}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <button
              type="button"
              data-tour="workflow-continue-shortcut"
              onClick={startNextTour}
              className="flex items-center gap-1.5 rounded-full border border-primary/50 bg-card/95 px-2.5 py-1 text-[10px] font-medium text-primary shadow-lg shadow-primary/20 backdrop-blur-md transition-colors hover:bg-primary/10"
            >
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-70" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
              </span>
              <span>Continue tour</span>
            </button>
          </motion.div>
          {showWorkflowTourPrompt && workflowCueRect && (
            <motion.div
              className="fixed z-[71] w-[320px] rounded-2xl border border-border/70 bg-card/95 p-4 text-card-foreground shadow-2xl shadow-black/30 backdrop-blur-xl"
              style={{
                left: Math.min(workflowCueRect.left + workflowCueRect.width + 18, window.innerWidth - 340),
                top: Math.max(92, Math.min(workflowCueRect.top - 8, window.innerHeight - 210)),
              }}
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="mb-2 flex items-center gap-2 text-primary">
                <Sparkles className="h-4 w-4" />
                <span className="text-[10px] font-medium uppercase tracking-[0.18em]">Next tour</span>
              </div>
              <p className="text-sm font-semibold text-foreground">{nextTourCopy.title}</p>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">{nextTourCopy.body}</p>
              <div className="mt-4 flex items-center justify-end gap-2">
                <button type="button" onClick={dismissWorkflowTourPrompt} className="rounded-lg px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground">Skip for now</button>
                <button type="button" onClick={startNextTour} className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90">{nextTourCopy.cta}</button>
              </div>
            </motion.div>
          )}
        </>
      )}

      {/* Toggle */}
      <button onClick={toggleSidebar}
        className="h-10 flex items-center justify-center border-t border-sidebar-border text-muted-foreground hover:text-foreground transition-colors">
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </motion.aside>
    <MeetDanyelModal isOpen={isBuilderOpen} onClose={() => setIsBuilderOpen(false)} />
    </>
  );
}

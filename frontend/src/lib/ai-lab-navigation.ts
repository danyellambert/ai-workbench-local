import {
  LayoutGrid, Server, MessageSquare, Workflow, BarChart3,
  ShieldCheck, Archive, Terminal
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface AiLabRoute {
  key: string;
  label: string;
  path: string;
  icon: LucideIcon;
  description: string;
  operatorQuestion: string;
}

export const AI_LAB_ROUTES: AiLabRoute[] = [
  {
    key: 'overview',
    label: 'Overview',
    path: '/app/lab/overview',
    icon: LayoutGrid,
    description: 'AI Engineering Operating Console',
    operatorQuestion: 'What needs attention right now?',
  },
  {
    key: 'runtime',
    label: 'Runtime & Observability',
    path: '/app/lab/runtime',
    icon: Server,
    description: 'Runtime health, configuration and diagnostics',
    operatorQuestion: 'Is the runtime healthy and cost-controlled?',
  },
  {
    key: 'chat',
    label: 'Document Experiments',
    path: '/app/lab/chat',
    icon: MessageSquare,
    description: 'RAG and document interaction diagnostics',
    operatorQuestion: 'Is RAG helping or just adding noise and cost?',
  },
  {
    key: 'workflow-inspector',
    label: 'Workflow Inspector',
    path: '/app/lab/workflow-inspector',
    icon: Workflow,
    description: 'Structured execution, routing and auditability',
    operatorQuestion: 'Why did the workflow choose this route, and what triggered review?',
  },
  {
    key: 'benchmarks',
    label: 'Benchmarks',
    path: '/app/lab/benchmarks',
    icon: BarChart3,
    description: 'Model and strategy comparison hub',
    operatorQuestion: 'Which model/provider setup is strongest for which use case?',
  },
  {
    key: 'evals',
    label: 'Evals & Diagnosis',
    path: '/app/lab/evals',
    icon: ShieldCheck,
    description: 'Quality measurement and regression control',
    operatorQuestion: 'Where has quality regressed?',
  },
  {
    key: 'artifacts',
    label: 'Experiments & Artifacts',
    path: '/app/lab/artifacts',
    icon: Archive,
    description: 'Technical evidence and experimentation archive',
    operatorQuestion: 'Where is the technical evidence that explains current behavior?',
  },
  {
    key: 'evidenceops',
    label: 'MCP Operations',
    path: '/app/lab/evidenceops',
    icon: Terminal,
    description: 'Operations, governance and MCP console',
    operatorQuestion: 'Is operations/governance healthy and controllable?',
  },
];

export const AI_LAB_ROUTE_MAP: Record<string, AiLabRoute> = Object.fromEntries(
  AI_LAB_ROUTES.map(r => [r.path, r])
);

// Legacy aliases
export const AI_LAB_REDIRECTS: Record<string, string> = {
  '/app/lab/structured': '/app/lab/workflow-inspector',
  '/app/lab/models': '/app/lab/benchmarks',
};

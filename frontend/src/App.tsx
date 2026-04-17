import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { MotionConfig } from 'framer-motion';
import { useEffect } from 'react';
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import LandingPage from "@/pages/LandingPage";
import AppShell from "@/components/layout/AppShell";
import OverviewPage from "@/pages/OverviewPage";
import DocumentsPage from "@/pages/DocumentsPage";
import WorkflowCatalogPage from "@/pages/WorkflowCatalogPage";
import DocumentReviewPage from "@/pages/DocumentReviewPage";
import ComparisonPage from "@/pages/ComparisonPage";
import ActionPlanPage from "@/pages/ActionPlanPage";
import CandidateReviewPage from "@/pages/CandidateReviewPage";
import DeckCenterPage from "@/pages/DeckCenterPage";
import RunHistoryPage from "@/pages/RunHistoryPage";
import ChatPage from "@/pages/ChatPage";
import LabOverviewPage from "@/pages/LabOverviewPage";
import RuntimeObservabilityPage from "@/pages/RuntimeObservabilityPage";
import WorkflowInspectorPage from "@/pages/WorkflowInspectorPage";
import BenchmarksPage from "@/pages/BenchmarksPage";
import EvalsDiagnosisPage from "@/pages/EvalsDiagnosisPage";
import AdvancedExperimentsPage from "@/pages/AdvancedExperimentsPage";
import EvidenceOpsPage from "@/pages/EvidenceOpsPage";
import RuntimeControlsPage from "@/pages/RuntimeControlsPage";
import PreferencesPage from "@/pages/PreferencesPage";
import { getPreferences } from '@/lib/product-api';
import { useAppStore } from '@/lib/store';
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function PreferencesBootstrap() {
  const setGlobalPreferences = useAppStore((state) => state.setGlobalPreferences);
  const { data } = useQuery({
    queryKey: ['preferences'],
    queryFn: getPreferences,
    retry: false,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    setGlobalPreferences(data ?? null);
  }, [data, setGlobalPreferences]);

  return null;
}

const App = () => {
  const reducedMotion = useAppStore((state) => state.operatorPreferences.reducedMotion);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <PreferencesBootstrap />
        <MotionConfig reducedMotion={reducedMotion ? 'always' : 'never'}>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/app" element={<AppShell />}>
                <Route index element={<OverviewPage />} />
                <Route path="documents" element={<DocumentsPage />} />
                <Route path="workflows" element={<WorkflowCatalogPage />} />
                <Route path="workflows/document-review" element={<DocumentReviewPage />} />
                <Route path="workflows/comparison" element={<ComparisonPage />} />
                <Route path="workflows/action-plan" element={<ActionPlanPage />} />
                <Route path="workflows/candidate-review" element={<CandidateReviewPage />} />
                <Route path="deck-center" element={<DeckCenterPage />} />
                <Route path="history" element={<RunHistoryPage />} />
                <Route path="lab/overview" element={<LabOverviewPage />} />
                <Route path="lab/runtime" element={<RuntimeObservabilityPage />} />
                <Route path="lab/chat" element={<ChatPage />} />
                <Route path="lab/workflow-inspector" element={<WorkflowInspectorPage />} />
                <Route path="lab/benchmarks" element={<BenchmarksPage />} />
                <Route path="lab/evals" element={<EvalsDiagnosisPage />} />
                <Route path="lab/artifacts" element={<AdvancedExperimentsPage />} />
                <Route path="lab/evidenceops" element={<EvidenceOpsPage />} />
                <Route path="lab/structured" element={<Navigate to="/app/lab/workflow-inspector" replace />} />
                <Route path="lab/models" element={<Navigate to="/app/lab/benchmarks" replace />} />
                <Route path="settings/runtime" element={<RuntimeControlsPage />} />
                <Route path="settings/preferences" element={<PreferencesPage />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </MotionConfig>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;

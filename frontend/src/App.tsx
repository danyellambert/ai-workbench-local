import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
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
import StructuredOutputsPage from "@/pages/StructuredOutputsPage";
import ModelComparisonPage from "@/pages/ModelComparisonPage";
import EvidenceOpsPage from "@/pages/EvidenceOpsPage";
import SettingsPage from "@/pages/SettingsPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
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
            <Route path="lab/chat" element={<ChatPage />} />
            <Route path="lab/structured" element={<StructuredOutputsPage />} />
            <Route path="lab/models" element={<ModelComparisonPage />} />
            <Route path="lab/evidenceops" element={<EvidenceOpsPage />} />
            <Route path="settings/runtime" element={<SettingsPage />} />
            <Route path="settings/preferences" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

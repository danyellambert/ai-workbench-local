import { create } from 'zustand';

import type { PreferencesResponse } from '@/lib/product-api';
import type { OperatorPreferences } from '@/types/settings';

const DEFAULT_OPERATOR_PREFERENCES: OperatorPreferences = {
  reducedMotion: false,
  defaultEvidencePanelOpen: true,
  defaultExportFormat: 'pptx',
  defaultBenchmarkBaseline: '',
  showSourceBadges: true,
  autoOpenInspectorDetails: false,
};

interface AppState {
  sidebarOpen: boolean;
  commandPaletteOpen: boolean;
  runtimeDrawerOpen: boolean;
  operatorPreferences: OperatorPreferences;
  preferencesLoaded: boolean;
  benchmarkBaselineLabel: string;
  toggleSidebar: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setRuntimeDrawerOpen: (open: boolean) => void;
  setGlobalPreferences: (payload: PreferencesResponse | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  commandPaletteOpen: false,
  runtimeDrawerOpen: false,
  operatorPreferences: DEFAULT_OPERATOR_PREFERENCES,
  preferencesLoaded: false,
  benchmarkBaselineLabel: '',
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setRuntimeDrawerOpen: (open) => set({ runtimeDrawerOpen: open }),
  setGlobalPreferences: (payload) => set(() => {
    const operatorPreferences = payload?.operator_preferences ?? DEFAULT_OPERATOR_PREFERENCES;
    const profiles = payload?.runtime_profiles ?? [];
    const benchmarkBaselineLabel = profiles.find((profile) => profile.id === operatorPreferences.defaultBenchmarkBaseline)?.name || '';
    return {
      operatorPreferences,
      preferencesLoaded: Boolean(payload),
      benchmarkBaselineLabel,
    };
  }),
}));

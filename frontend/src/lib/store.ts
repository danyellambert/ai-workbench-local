import { create } from 'zustand';

interface AppState {
  sidebarOpen: boolean;
  commandPaletteOpen: boolean;
  runtimeDrawerOpen: boolean;
  toggleSidebar: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setRuntimeDrawerOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  commandPaletteOpen: false,
  runtimeDrawerOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setRuntimeDrawerOpen: (open) => set({ runtimeDrawerOpen: open }),
}));

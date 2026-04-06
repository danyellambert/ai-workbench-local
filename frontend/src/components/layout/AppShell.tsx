import { Outlet } from 'react-router-dom';
import AppSidebar from './AppSidebar';
import TopBar from './TopBar';
import CommandPalette from './CommandPalette';
import RuntimeDrawer from './RuntimeDrawer';
import AuroraBackground from './AuroraBackground';

export default function AppShell() {
  return (
    <div className="min-h-screen flex w-full">
      <AuroraBackground />
      <AppSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
      <RuntimeDrawer />
    </div>
  );
}

import { Outlet } from 'react-router-dom';
import Sidebar from '@/components/layout/Sidebar';
import BottomTabs from '@/components/mobile/BottomTabs';

export default function AppLayout({ role, userName }) {
  const showBottomTabs = role === 'student' || role === 'teacher';
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar role={role} userName={userName} />
      <main className="flex-1 overflow-auto" style={{ paddingBottom: showBottomTabs ? '80px' : undefined }}>
        <Outlet />
      </main>
      {showBottomTabs && <BottomTabs role={role} />}
    </div>
  );
}

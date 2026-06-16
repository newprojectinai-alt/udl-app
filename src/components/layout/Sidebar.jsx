import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { BarChart3, BookOpen, Brain, GraduationCap, LayoutDashboard, LogOut, Menu, Upload, Users, X } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';

const navGroups = {
  admin: [
    { label: 'Dashboard', icon: LayoutDashboard, path: '/admin' },
    { label: 'Upload Textbooks', icon: Upload, path: '/admin/textbooks' },
    { label: 'Manage Users', icon: Users, path: '/admin/users' },
    { label: 'Reports', icon: BarChart3, path: '/admin/reports' },
  ],
  teacher: [
    { label: 'Dashboard', icon: LayoutDashboard, path: '/teacher' },
    { label: 'My Students', icon: Users, path: '/teacher/students' },
    { label: 'Reports', icon: BarChart3, path: '/teacher/reports' },
  ],
  student: [
    { label: 'Dashboard', icon: LayoutDashboard, path: '/student' },
    { label: 'My Lessons', icon: BookOpen, path: '/student/lessons' },
    { label: 'Assessments', icon: Brain, path: '/student/assessments' },
    { label: 'Progress', icon: BarChart3, path: '/student/progress' },
  ],
};

const roleColors = {
  admin: 'from-violet-600 to-purple-700',
  teacher: 'from-emerald-600 to-teal-700',
  student: 'from-blue-600 to-indigo-700',
};

export default function Sidebar({ role = 'student', userName = '' }) {
  const location = useLocation();
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);
  const items = navGroups[role] || navGroups.student;

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      <div className={`p-6 bg-gradient-to-br ${roleColors[role]}`}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center"><GraduationCap className="w-5 h-5 text-white" /></div>
          <div><p className="font-poppins font-bold text-white text-lg leading-none">UDL Learn</p><p className="text-white/70 text-xs capitalize mt-0.5">{role} portal</p></div>
        </div>
        {userName && <div className="mt-4 pt-4 border-t border-white/20"><p className="text-white/60 text-xs">Welcome back,</p><p className="text-white font-semibold text-sm truncate">{userName}</p></div>}
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {items.map((item) => {
          const active = location.pathname === item.path;
          return <Link key={item.path} to={item.path} onClick={() => setOpen(false)} className={cn('flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all', active ? 'bg-sidebar-primary text-sidebar-primary-foreground' : 'text-sidebar-foreground hover:bg-sidebar-accent')}><item.icon className="w-4 h-4" />{item.label}</Link>;
        })}
      </nav>
      <div className="p-4 border-t border-sidebar-border"><button onClick={logout} className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent"><LogOut className="w-4 h-4" />Sign out</button></div>
    </div>
  );

  return (
    <>
      <button className="fixed top-4 left-4 z-50 md:hidden bg-card border border-border rounded-xl p-2 shadow-sm" onClick={() => setOpen(!open)}>{open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}</button>
      {open && <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={() => setOpen(false)} />}
      <div className={cn('fixed inset-y-0 left-0 z-40 w-64 bg-sidebar transition-transform md:hidden', open ? 'translate-x-0' : '-translate-x-full')}><SidebarContent /></div>
      <div className="hidden md:flex flex-col w-64 bg-sidebar h-screen sticky top-0 shrink-0"><SidebarContent /></div>
    </>
  );
}

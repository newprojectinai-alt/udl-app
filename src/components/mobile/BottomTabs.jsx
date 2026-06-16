import { Link, useLocation } from 'react-router-dom';
import { BarChart3, BookOpen, Brain, LayoutDashboard, Users } from 'lucide-react';
import { cn } from '@/lib/utils';

const studentTabs = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/student' },
  { label: 'Lessons', icon: BookOpen, path: '/student/lessons' },
  { label: 'Assessments', icon: Brain, path: '/student/assessments' },
  { label: 'Progress', icon: BarChart3, path: '/student/progress' },
];
const teacherTabs = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/teacher' },
  { label: 'Students', icon: Users, path: '/teacher/students' },
  { label: 'Reports', icon: BarChart3, path: '/teacher/reports' },
];

export default function BottomTabs({ role }) {
  const location = useLocation();
  const tabs = role === 'teacher' ? teacherTabs : studentTabs;
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-card border-t border-border flex">
      {tabs.map((tab) => {
        const active = location.pathname === tab.path;
        return <Link key={tab.path} to={tab.path} className={cn('flex-1 flex flex-col items-center justify-center py-2.5 gap-1 text-xs font-medium', active ? 'text-primary' : 'text-muted-foreground')}><tab.icon className="w-5 h-5" /><span>{tab.label}</span></Link>;
      })}
    </nav>
  );
}

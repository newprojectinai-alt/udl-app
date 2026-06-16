import { useQuery } from '@tanstack/react-query';
import { assessmentService, studentService, textbookService } from '@/services/entityService';
import { BarChart3, BookOpen, CheckCircle, FileText, TrendingUp, Upload, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const SUBJECTS = ['Mathematics', 'Science', 'English', 'Social Studies', 'Hindi', 'Computer Science'];

export default function AdminDashboard() {
  const { data: textbooks = [] } = useQuery({ queryKey: ['textbooks'], queryFn: () => textbookService.list() });
  const { data: students = [] } = useQuery({ queryKey: ['students'], queryFn: () => studentService.list() });
  const { data: assessments = [] } = useQuery({ queryKey: ['assessments'], queryFn: () => assessmentService.list() });
  const stats = [
    { label: 'Textbooks Uploaded', value: textbooks.length, icon: BookOpen, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Students Enrolled', value: students.length, icon: Users, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Assessments Taken', value: assessments.length, icon: FileText, color: 'text-violet-600', bg: 'bg-violet-50' },
    { label: 'Ready Textbooks', value: textbooks.filter((item) => item.status === 'ready').length, icon: CheckCircle, color: 'text-teal-600', bg: 'bg-teal-50' },
  ];
  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <div className="mb-8"><h1 className="font-poppins font-bold text-2xl">Admin Dashboard</h1><p className="text-muted-foreground text-sm mt-1">Platform overview and management</p></div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">{stats.map((stat, index) => <motion.div key={stat.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }} className="bg-card border border-border rounded-2xl p-5"><div className={`w-10 h-10 ${stat.bg} rounded-xl flex items-center justify-center mb-3`}><stat.icon className={`w-5 h-5 ${stat.color}`} /></div><p className="font-poppins font-bold text-2xl">{stat.value}</p><p className="text-muted-foreground text-xs mt-1">{stat.label}</p></motion.div>)}</div>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-2xl p-6"><h2 className="font-semibold mb-4">Quick Actions</h2><div className="space-y-3">{[{ to: '/admin/textbooks', icon: Upload, title: 'Upload New Textbook', desc: 'Add PDF for any class/subject' }, { to: '/admin/users', icon: Users, title: 'Manage Users', desc: 'View students and teachers' }, { to: '/admin/reports', icon: TrendingUp, title: 'View Reports', desc: 'Platform analytics' }].map((item) => <Link key={item.to} to={item.to} className="flex items-center gap-3 p-3 rounded-xl hover:bg-muted"><div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center"><item.icon className="w-4 h-4 text-blue-600" /></div><div><p className="text-sm font-medium">{item.title}</p><p className="text-xs text-muted-foreground">{item.desc}</p></div></Link>)}</div></div>
        <div className="bg-card border border-border rounded-2xl p-6"><h2 className="font-semibold mb-4">Textbooks by Subject</h2><div className="space-y-3">{SUBJECTS.map((subject) => { const count = textbooks.filter((item) => item.subject === subject).length; return <div key={subject} className="flex items-center justify-between"><span className="text-sm">{subject}</span><div className="flex items-center gap-2"><div className="w-24 h-2 bg-muted rounded-full overflow-hidden"><div className="h-full bg-primary rounded-full" style={{ width: `${Math.min(100, count * 20)}%` }} /></div><span className="text-xs text-muted-foreground w-4">{count}</span></div></div>; })}</div></div>
      </div>
      <div className="mt-6 bg-card border border-border rounded-2xl p-6"><h2 className="font-semibold mb-4">Recent Textbooks</h2>{textbooks.length === 0 ? <p className="text-sm text-muted-foreground">No textbooks uploaded yet.</p> : <div className="space-y-2">{textbooks.slice(0, 5).map((item) => <div key={item.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-muted"><div><p className="text-sm font-medium">{item.title}</p><p className="text-xs text-muted-foreground">Class {item.class_level} · {item.subject}</p></div><span className="text-xs px-2 py-1 rounded-full bg-emerald-50 text-emerald-600">{item.status}</span></div>)}</div>}</div>
    </div>
  );
}

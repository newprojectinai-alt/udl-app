import { useQuery } from '@tanstack/react-query';
import { studentService, teacherService } from '@/services/entityService';
import { BookOpen, GraduationCap } from 'lucide-react';

export default function AdminUsers() {
  const { data: students = [] } = useQuery({ queryKey: ['students'], queryFn: () => studentService.list() });
  const { data: teachers = [] } = useQuery({ queryKey: ['teachers'], queryFn: () => teacherService.list() });
  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      <div className="mb-8"><h1 className="font-poppins font-bold text-2xl">Manage Users</h1><p className="text-muted-foreground text-sm mt-1">All registered students and teachers</p></div>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-2xl p-6"><div className="flex items-center gap-2 mb-5"><GraduationCap className="w-5 h-5 text-blue-600" /><h2 className="font-semibold">Students ({students.length})</h2></div><div className="space-y-3">{students.map((student) => <div key={student.id} className="p-3 rounded-xl border border-border"><div className="flex justify-between"><p className="font-medium text-sm">{student.full_name || student.user_email}</p><span className="text-xs text-muted-foreground">Class {student.class_level}</span></div><p className="text-xs text-muted-foreground mt-1">{student.iq_level} · {(student.disability_types || []).join(', ') || 'no special needs selected'}</p></div>)}</div></div>
        <div className="bg-card border border-border rounded-2xl p-6"><div className="flex items-center gap-2 mb-5"><BookOpen className="w-5 h-5 text-emerald-600" /><h2 className="font-semibold">Teachers ({teachers.length})</h2></div><div className="space-y-3">{teachers.map((teacher) => <div key={teacher.id} className="p-3 rounded-xl border border-border"><p className="font-medium text-sm">{teacher.full_name || teacher.user_email}</p><p className="text-xs text-muted-foreground mt-1">{(teacher.subjects || []).join(', ') || 'No subjects assigned'}</p><p className="text-xs text-muted-foreground">Classes: {(teacher.class_levels || []).join(', ') || '—'}</p></div>)}</div></div>
      </div>
    </div>
  );
}

import { useQuery } from '@tanstack/react-query';
import { assessmentService, studentService } from '@/services/entityService';
import { AlertTriangle, Brain, Ear, Eye, Search, ShieldCheck, Users } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useState } from 'react';

const disabilityIcon = { visual: Eye, hearing: Ear, cognitive: Brain };

export default function TeacherStudents() {
  const [search, setSearch] = useState('');
  const { data: students = [] } = useQuery({ queryKey: ['students'], queryFn: () => studentService.list() });
  const { data: assessments = [] } = useQuery({ queryKey: ['completedAssessments'], queryFn: () => assessmentService.filter({ completed: true }) });
  const filtered = students.filter((student) => (student.full_name || student.user_email || '').toLowerCase().includes(search.toLowerCase()));
  const supportCount = students.filter((student) => getStudentAnalytics(student.user_email, assessments).priority !== 'stable').length;

  return (
    <div className="min-h-screen edu-animated-bg p-6 md:p-8">
      <div className="edu-grid-overlay" />
      <div className="relative z-10 max-w-5xl mx-auto">
        <div className="motion-pop mb-8 rounded-3xl bg-gradient-to-r from-emerald-600 to-teal-600 p-6 text-white shadow-2xl shadow-emerald-500/20">
          <p className="text-white/80 text-sm">Teacher care dashboard</p>
          <h1 className="font-poppins font-bold text-3xl">My Students</h1>
          <p className="text-white/90 text-sm mt-1">{students.length} students · {supportCount} need extra support</p>
        </div>

        <div className="relative mb-5">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search students..." className="pl-9 bg-white/90" />
        </div>

        {filtered.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground bg-white/80 rounded-3xl"><Users className="w-10 h-10 mx-auto mb-2 opacity-30" /><p className="text-sm">No students found</p></div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {filtered.map((student) => {
              const analytics = getStudentAnalytics(student.user_email, assessments);
              const alertStyle = analytics.priority === 'high' ? 'bg-red-50 text-red-700 border-red-200' : analytics.priority === 'watch' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200';
              return (
                <div key={student.id} className="bg-white/90 border border-white/70 rounded-3xl p-5 shadow-sm">
                  <div className="flex justify-between mb-3">
                    <div>
                      <p className="font-semibold">{student.full_name || student.user_email}</p>
                      <p className="text-xs text-muted-foreground">Class {student.class_level} · {analytics.records.length} assessments</p>
                    </div>
                    <div className="text-right">
                      <p className={`font-bold text-xl ${analytics.avgScore !== null && analytics.avgScore < 60 ? 'text-red-500' : 'text-primary'}`}>{analytics.avgScore !== null ? `${analytics.avgScore}%` : 'N/A'}</p>
                      <p className="text-xs text-muted-foreground">avg score</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {(student.disability_types || []).map((type) => { const Icon = disabilityIcon[type] || Brain; return <span key={type} className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border capitalize bg-white"><Icon className="w-3 h-3" />{type}</span>; })}
                    <span className="text-xs px-2.5 py-1 rounded-full bg-muted capitalize">{student.iq_level}</span>
                  </div>

                  <div className={`rounded-2xl border px-3 py-2 text-xs ${alertStyle}`}>
                    <div className="flex items-center gap-2 font-semibold">
                      {analytics.priority === 'stable' ? <ShieldCheck className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                      {analytics.message}
                    </div>
                    {analytics.weakChapter && <p className="mt-1">Suggested care: revise “{analytics.weakChapter}” with a short 1:1 session.</p>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function getStudentAnalytics(email, assessments) {
  const records = assessments.filter((item) => item.student_email === email);
  if (!records.length) return { records, avgScore: null, priority: 'watch', message: 'No completed assessments yet', weakChapter: null };
  const scored = records.map((item) => ({ ...item, pct: Math.round(((item.score || 0) / (item.total_questions || 1)) * 100) }));
  const avgScore = Math.round(scored.reduce((sum, item) => sum + item.pct, 0) / scored.length);
  const weak = [...scored].sort((a, b) => a.pct - b.pct)[0];
  if (avgScore < 50) return { records, avgScore, priority: 'high', message: 'High support priority', weakChapter: weak?.chapter };
  if (avgScore < 65) return { records, avgScore, priority: 'watch', message: 'Needs extra practice', weakChapter: weak?.chapter };
  return { records, avgScore, priority: 'stable', message: 'Learning is stable', weakChapter: weak?.pct < 60 ? weak.chapter : null };
}

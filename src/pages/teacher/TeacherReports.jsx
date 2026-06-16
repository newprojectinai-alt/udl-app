import { useQuery } from '@tanstack/react-query';
import { assessmentService, studentService } from '@/services/entityService';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function TeacherReports() {
  const { data: students = [] } = useQuery({ queryKey: ['students'], queryFn: () => studentService.list() });
  const { data: assessments = [] } = useQuery({ queryKey: ['completedAssessments'], queryFn: () => assessmentService.filter({ completed: true }) });
  const subjectData = [...new Set(assessments.map((item) => item.subject))].map((subject) => ({ subject: subject?.slice(0, 8), avg: assessments.filter((item) => item.subject === subject).reduce((sum, item) => sum + (item.score / (item.total_questions || 1)) * 100, 0) / Math.max(1, assessments.filter((item) => item.subject === subject).length) }));
  const riskStudents = students.filter((student) => {
    const records = assessments.filter((item) => item.student_email === student.user_email);
    if (!records.length) return false;
    return records.reduce((sum, item) => sum + (item.score / (item.total_questions || 1)) * 100, 0) / records.length < 60;
  });
  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto"><div className="mb-8"><h1 className="font-poppins font-bold text-2xl">Teacher Reports</h1><p className="text-muted-foreground text-sm mt-1">Class performance and intervention planning.</p></div><div className="grid md:grid-cols-3 gap-4 mb-8">{[{ label: 'Students', value: students.length }, { label: 'Completed Assessments', value: assessments.length }, { label: 'Need Special Care', value: riskStudents.length }].map((stat) => <div key={stat.label} className="bg-card border rounded-2xl p-5 text-center"><p className="font-bold text-3xl">{stat.value}</p><p className="text-xs text-muted-foreground">{stat.label}</p></div>)}</div><div className="bg-card border rounded-2xl p-6 mb-6"><h2 className="font-semibold mb-4">Average Score by Subject</h2><ResponsiveContainer width="100%" height={260}><BarChart data={subjectData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="subject" /><YAxis domain={[0, 100]} /><Tooltip /><Bar dataKey="avg" fill="#10b981" /></BarChart></ResponsiveContainer></div><div className="bg-card border rounded-2xl p-6"><h2 className="font-semibold mb-4">Students Needing Support</h2>{riskStudents.length ? <div className="space-y-3">{riskStudents.map((student) => <div key={student.id} className="p-3 border rounded-xl"><p className="font-medium text-sm">{student.full_name || student.user_email}</p><p className="text-xs text-muted-foreground">Class {student.class_level} · {student.iq_level} level</p></div>)}</div> : <p className="text-sm text-muted-foreground">No students currently flagged.</p>}</div></div>
  );
}

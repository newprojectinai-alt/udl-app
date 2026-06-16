import { useQuery } from '@tanstack/react-query';
import { assessmentService, studentService } from '@/services/entityService';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b'];
const SUBJECTS = ['Mathematics', 'Science', 'English', 'Social Studies', 'Hindi', 'Computer Science'];

export default function AdminReports() {
  const { data: assessments = [] } = useQuery({ queryKey: ['assessments'], queryFn: () => assessmentService.list() });
  const { data: students = [] } = useQuery({ queryKey: ['students'], queryFn: () => studentService.list() });
  const completed = assessments.filter((item) => item.completed);
  const subjectData = SUBJECTS.map((subject) => {
    const subjectAssessments = completed.filter((item) => item.subject === subject);
    return { subject: subject.slice(0, 4), avg: subjectAssessments.reduce((sum, item) => sum + (item.score / (item.total_questions || 1)) * 100, 0) / Math.max(1, subjectAssessments.length) };
  });
  const iqData = ['basic', 'standard', 'advanced'].map((level) => ({ name: level, value: students.filter((item) => item.iq_level === level).length }));
  const avgScore = completed.length ? (completed.reduce((sum, item) => sum + (item.score / (item.total_questions || 1)) * 100, 0) / completed.length).toFixed(1) : 0;
  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      <div className="mb-8"><h1 className="font-poppins font-bold text-2xl">Platform Reports</h1><p className="text-muted-foreground text-sm mt-1">Assessment analytics and student distribution</p></div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">{[{ label: 'Total Assessments', value: assessments.length }, { label: 'Completed', value: completed.length }, { label: 'Avg Score', value: `${avgScore}%` }, { label: 'Students', value: students.length }].map((stat) => <div key={stat.label} className="bg-card border border-border rounded-2xl p-5 text-center"><p className="font-poppins font-bold text-3xl">{stat.value}</p><p className="text-xs text-muted-foreground mt-1">{stat.label}</p></div>)}</div>
      <div className="grid md:grid-cols-2 gap-6"><div className="bg-card border border-border rounded-2xl p-6"><h2 className="font-semibold mb-4">Avg Score by Subject</h2><ResponsiveContainer width="100%" height={220}><BarChart data={subjectData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="subject" /><YAxis /><Tooltip formatter={(value) => [`${value.toFixed(1)}%`, 'Avg Score']} /><Bar dataKey="avg" fill="#3b82f6" /></BarChart></ResponsiveContainer></div><div className="bg-card border border-border rounded-2xl p-6"><h2 className="font-semibold mb-4">Students by IQ Level</h2><ResponsiveContainer width="100%" height={220}><PieChart><Pie data={iqData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label>{iqData.map((_, index) => <Cell key={index} fill={COLORS[index]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div></div>
    </div>
  );
}

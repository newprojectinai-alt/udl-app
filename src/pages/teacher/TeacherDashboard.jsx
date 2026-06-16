import { useQuery } from '@tanstack/react-query';
import { assessmentService, studentService } from '@/services/entityService';
import { AlertTriangle, BarChart3, CheckCircle, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function TeacherDashboard() {
  const { data: students = [] } = useQuery({ queryKey: ['students'], queryFn: () => studentService.list() });
  const { data: assessments = [] } = useQuery({ queryKey: ['completedAssessments'], queryFn: () => assessmentService.filter({ completed: true }) });
  const avgScore = assessments.length ? (assessments.reduce((sum, item) => sum + (item.score / (item.total_questions || 1)) * 100, 0) / assessments.length).toFixed(0) : 0;
  const needsSupport = students.filter((student) => {
    const studentAssessments = assessments.filter((item) => item.student_email === student.user_email);
    if (!studentAssessments.length) return false;
    const score = studentAssessments.reduce((sum, item) => sum + (item.score / (item.total_questions || 1)) * 100, 0) / studentAssessments.length;
    return score < 60;
  });
  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <div className="mb-8"><h1 className="font-poppins font-bold text-2xl">Teacher Dashboard</h1><p className="text-muted-foreground text-sm mt-1">Monitor student progress and identify support needs.</p></div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">{[{ label: 'Students', value: students.length, icon: Users }, { label: 'Assessments', value: assessments.length, icon: CheckCircle }, { label: 'Avg Score', value: `${avgScore}%`, icon: BarChart3 }, { label: 'Need Support', value: needsSupport.length, icon: AlertTriangle }].map((stat) => <div key={stat.label} className="bg-card border rounded-2xl p-5"><stat.icon className="w-5 h-5 text-primary mb-3" /><p className="font-bold text-2xl">{stat.value}</p><p className="text-xs text-muted-foreground">{stat.label}</p></div>)}</div>
      <div className="grid md:grid-cols-2 gap-6"><Link to="/teacher/students" className="bg-card border rounded-2xl p-6 hover:shadow-md"><Users className="w-8 h-8 text-primary mb-4" /><h2 className="font-semibold mb-1">View Students</h2><p className="text-sm text-muted-foreground">Review student accessibility profiles and scores.</p></Link><Link to="/teacher/reports" className="bg-card border rounded-2xl p-6 hover:shadow-md"><BarChart3 className="w-8 h-8 text-primary mb-4" /><h2 className="font-semibold mb-1">View Reports</h2><p className="text-sm text-muted-foreground">Analyze class-level performance trends.</p></Link></div>
    </div>
  );
}

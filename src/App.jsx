import { Toaster } from '@/components/ui/toaster';
import ThemeProvider from '@/lib/ThemeProvider';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClientInstance } from '@/lib/query-client';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from '@/lib/PageNotFound';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import Landing from '@/pages/Landing';
import AdminDashboard from '@/pages/admin/AdminDashboard';
import TextbookUpload from '@/pages/admin/TextbookUpload';
import AdminUsers from '@/pages/admin/AdminUsers';
import AdminReports from '@/pages/admin/AdminReports';
import TeacherDashboard from '@/pages/teacher/TeacherDashboard';
import TeacherStudents from '@/pages/teacher/TeacherStudents';
import TeacherReports from '@/pages/teacher/TeacherReports';
import StudentDashboard from '@/pages/student/StudentDashboard';
import StudentLessons from '@/pages/student/StudentLessons';
import LessonView from '@/pages/student/LessonView';
import StudentAssessments from '@/pages/student/StudentAssessments';
import AssessmentSession from '@/pages/student/AssessmentSession';
import StudentProgress from '@/pages/student/StudentProgress';
import AppLayout from '@/components/layout/AppLayout';

const RoleLayout = ({ role }) => {
  const { user } = useAuth();
  return <AppLayout role={role} userName={user?.full_name || user?.email || ''} />;
};

function AuthenticatedApp() {
  const { isLoadingAuth } = useAuth();
  if (isLoadingAuth) {
    return <div className="fixed inset-0 flex items-center justify-center"><div className="w-8 h-8 border-4 border-muted border-t-primary rounded-full animate-spin" /></div>;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route element={<RoleLayout role="admin" />}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/textbooks" element={<TextbookUpload />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/reports" element={<AdminReports />} />
      </Route>
      <Route element={<RoleLayout role="teacher" />}>
        <Route path="/teacher" element={<TeacherDashboard />} />
        <Route path="/teacher/students" element={<TeacherStudents />} />
        <Route path="/teacher/reports" element={<TeacherReports />} />
      </Route>
      <Route element={<RoleLayout role="student" />}>
        <Route path="/student" element={<StudentDashboard />} />
        <Route path="/student/lessons" element={<StudentLessons />} />
        <Route path="/student/lesson/:lessonId" element={<LessonView />} />
        <Route path="/student/assessments" element={<StudentAssessments />} />
        <Route path="/student/assessment/:assessmentId" element={<AssessmentSession />} />
        <Route path="/student/progress" element={<StudentProgress />} />
      </Route>
      <Route path="*" element={<PageNotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <QueryClientProvider client={queryClientInstance}>
          <Router>
            <AuthenticatedApp />
          </Router>
          <Toaster />
        </QueryClientProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

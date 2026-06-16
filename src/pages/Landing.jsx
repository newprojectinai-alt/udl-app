import { GraduationCap } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/button';

export default function Landing() {
  const { switchRole } = useAuth();
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-emerald-50 flex items-center justify-center p-6">
      <div className="max-w-3xl text-center">
        <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-6"><GraduationCap className="w-9 h-9 text-white" /></div>
        <h1 className="font-poppins font-bold text-4xl md:text-5xl mb-4">UDL Learn</h1>
        <p className="text-muted-foreground mb-8">Inclusive AI-assisted textbook lessons, accessibility support, assessments, and teacher reports for classes 5 to 10.</p>
        <div className="grid md:grid-cols-3 gap-3">
          <Button onClick={() => switchRole('student')} size="lg">Enter as Student</Button>
          <Button onClick={() => switchRole('teacher')} variant="outline" size="lg">Enter as Teacher</Button>
          <Button onClick={() => switchRole('admin')} variant="outline" size="lg">Enter as Admin</Button>
        </div>
      </div>
    </div>
  );
}

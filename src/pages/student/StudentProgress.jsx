import { useQuery } from '@tanstack/react-query';
import { assessmentService } from '@/services/entityService';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Award, Brain, CheckCircle, Flame, Sparkles, Star, TrendingUp, Trophy } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

export default function StudentProgress() {
  const { user } = useAuth();
  const { data: assessments = [] } = useQuery({ queryKey: ['myProgress', user?.email], queryFn: () => assessmentService.filter({ student_email: user.email, completed: true }), enabled: !!user?.email });
  const avgScore = assessments.length ? (assessments.reduce((sum, item) => sum + getPercent(item), 0) / assessments.length).toFixed(1) : 0;
  const subjectData = [...new Set(assessments.map((item) => item.subject))].map((subject) => ({
    subject: subject?.slice(0, 8) || 'N/A',
    avg: assessments.filter((item) => item.subject === subject).reduce((sum, item) => sum + getPercent(item), 0) / Math.max(1, assessments.filter((item) => item.subject === subject).length),
  }));
  const recent = [...assessments].sort((a, b) => new Date(b.created_at || b.created_date) - new Date(a.created_at || a.created_date)).slice(0, 10);
  const bestScore = assessments.length ? Math.max(...assessments.map(getPercent)) : 0;
  const badges = getBadges(assessments, Number(avgScore), bestScore);
  const weakSubjects = subjectData.filter((item) => item.avg < 60);

  return (
    <div className="min-h-screen edu-animated-bg p-6 md:p-8">
      <div className="edu-grid-overlay" />
      <div className="relative z-10 max-w-5xl mx-auto">
        <div className="motion-pop mb-8 rounded-3xl bg-gradient-to-r from-violet-600 to-blue-600 p-6 text-white shadow-2xl shadow-blue-500/20">
          <p className="text-white/80 text-sm">Your learning journey</p>
          <h1 className="font-poppins font-bold text-3xl">My Progress</h1>
          <p className="text-white/90 text-sm mt-1">Track scores, badges, feedback, and what to practice next.</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Completed', value: assessments.length, icon: CheckCircle, color: 'text-emerald-600' },
            { label: 'Avg Score', value: `${avgScore}%`, icon: TrendingUp, color: 'text-blue-600' },
            { label: 'Best Score', value: assessments.length ? `${bestScore}%` : '—', icon: Trophy, color: 'text-amber-500' },
            { label: 'Subjects', value: new Set(assessments.map((item) => item.subject)).size, icon: Brain, color: 'text-violet-600' },
          ].map((stat) => <div key={stat.label} className="bg-white/90 border border-white/70 rounded-3xl p-5 shadow-sm"><stat.icon className={`w-5 h-5 ${stat.color} mb-3`} /><p className="font-bold text-2xl">{stat.value}</p><p className="text-xs text-muted-foreground">{stat.label}</p></div>)}
        </div>

        <div className="bg-white/90 border border-white/70 rounded-3xl p-6 mb-6 shadow-sm">
          <h2 className="font-semibold mb-4 flex items-center gap-2"><Award className="w-5 h-5 text-amber-500" />Badges Earned</h2>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
            {badges.map((badge) => <div key={badge.label} className={`rounded-2xl p-4 border ${badge.earned ? 'bg-amber-50 border-amber-200' : 'bg-muted/40 border-border opacity-60'}`}><badge.icon className={`w-6 h-6 mb-2 ${badge.earned ? 'text-amber-500' : 'text-muted-foreground'}`} /><p className="font-semibold text-sm">{badge.label}</p><p className="text-xs text-muted-foreground mt-1">{badge.desc}</p></div>)}
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="bg-white/90 border border-white/70 rounded-3xl p-6 shadow-sm">
            <h2 className="font-semibold mb-4">Score by Subject</h2>
            <ResponsiveContainer width="100%" height={220}><BarChart data={subjectData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="subject" /><YAxis domain={[0, 100]} /><Tooltip /><Bar dataKey="avg" fill="#3b82f6" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer>
          </div>
          <div className="bg-white/90 border border-white/70 rounded-3xl p-6 shadow-sm">
            <h2 className="font-semibold mb-4">Practice Suggestions</h2>
            {weakSubjects.length ? <div className="space-y-3">{weakSubjects.map((item) => <div key={item.subject} className="rounded-2xl bg-red-50 text-red-700 p-3 text-sm">Practice more in {item.subject}. Current average: {Math.round(item.avg)}%</div>)}</div> : <p className="text-sm bg-emerald-50 text-emerald-700 rounded-2xl p-4">Great balance! Keep practicing regularly.</p>}
            {recent[0]?.ai_feedback && <div className="mt-4 rounded-2xl bg-blue-50 text-blue-800 p-4 text-sm"><p className="font-semibold mb-1">Latest AI Feedback</p>{recent[0].ai_feedback}</div>}
          </div>
        </div>

        <div className="bg-white/90 border border-white/70 rounded-3xl p-6 shadow-sm">
          <h2 className="font-semibold mb-4">Assessment History</h2>
          <div className="space-y-3">{recent.map((item) => { const pct = getPercent(item); return <div key={item.id} className="flex justify-between p-3 rounded-2xl border bg-white"><div><p className="text-sm font-medium">{item.chapter}</p><p className="text-xs text-muted-foreground">{item.subject} · {item.assessment_type}</p></div><p className={`font-bold ${pct >= 80 ? 'text-emerald-600' : pct >= 60 ? 'text-blue-600' : 'text-red-500'}`}>{pct}%</p></div>; })}</div>
        </div>
      </div>
    </div>
  );
}

function getPercent(item) {
  return Math.round(((item.score || 0) / (item.total_questions || 1)) * 100);
}

function getBadges(assessments, avgScore, bestScore) {
  return [
    { label: 'First Step', desc: 'Complete 1 assessment', icon: Sparkles, earned: assessments.length >= 1 },
    { label: 'Practice Streak', desc: 'Complete 5 assessments', icon: Flame, earned: assessments.length >= 5 },
    { label: 'High Flyer', desc: 'Score 80% once', icon: Star, earned: bestScore >= 80 },
    { label: 'Steady Learner', desc: 'Average 70%+', icon: Trophy, earned: avgScore >= 70 },
  ];
}

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { assessmentService, studentService } from '@/services/entityService';
import { BarChart3, BookOpen, Brain, Ear, Eye, Lightbulb, Settings, Zap, ArrowRight } from 'lucide-react';
import DeleteAccountModal from '@/components/DeleteAccountModal';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/lib/AuthContext';
import { toast } from 'sonner';

const CLASSES = ['5', '6', '7', '8', '9', '10'];
const DISABILITY_OPTIONS = [
  { id: 'visual', label: 'Visual Impairment', icon: Eye, color: 'bg-blue-50 border-blue-200 text-blue-700' },
  { id: 'hearing', label: 'Hearing Impairment', icon: Ear, color: 'bg-violet-50 border-violet-200 text-violet-700' },
  { id: 'cognitive', label: 'Cognitive Difference', icon: Lightbulb, color: 'bg-amber-50 border-amber-200 text-amber-700' },
];
const IQ_LEVELS = ['basic', 'standard', 'advanced'];
const PREF_KEY = 'udl_accessibility_preferences';

export default function StudentDashboard() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [setupMode, setSetupMode] = useState(false);
  const [form, setForm] = useState({ class_level: '', disability_types: [], iq_level: 'standard' });
  const [prefs, setPrefs] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(PREF_KEY)) || { motion: 'on', contrast: 'soft', readingSpeed: 'normal' };
    } catch {
      return { motion: 'on', contrast: 'soft', readingSpeed: 'normal' };
    }
  });
  const { data: profiles = [] } = useQuery({ queryKey: ['myProfile', user?.email], queryFn: () => studentService.filter({ user_email: user.email }), enabled: !!user?.email });
  const profile = profiles[0];
  const { data: assessments = [] } = useQuery({ queryKey: ['myAssessments', user?.email], queryFn: () => assessmentService.filter({ student_email: user.email, completed: true }), enabled: !!user?.email });
  const saveMutation = useMutation({
    mutationFn: (data) => profile ? studentService.update(profile.id, data) : studentService.create({ ...data, user_email: user.email, full_name: user.full_name }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['myProfile'] }); setSetupMode(false); toast.success('Profile saved'); },
  });
  const toggleDisability = (id) => setForm((current) => ({ ...current, disability_types: current.disability_types.includes(id) ? current.disability_types.filter((item) => item !== id) : [...current.disability_types, id] }));
  const savePrefs = (nextPrefs) => {
    setPrefs(nextPrefs);
    localStorage.setItem(PREF_KEY, JSON.stringify(nextPrefs));
    toast.success('Accessibility preferences saved');
  };
  const avgScore = assessments.length ? (assessments.reduce((sum, item) => sum + (item.score / (item.total_questions || 1)) * 100, 0) / assessments.length).toFixed(0) : 0;

  if (!profile || setupMode) {
    const activeForm = { ...form, class_level: form.class_level || profile?.class_level || '', iq_level: form.iq_level || profile?.iq_level || 'standard', disability_types: form.disability_types.length ? form.disability_types : profile?.disability_types || [] };
    return (
      <div className="p-6 md:p-8 max-w-2xl mx-auto"><div className="mb-8"><h1 className="font-poppins font-bold text-2xl">{profile ? 'Edit Your Profile' : 'Welcome to UDL Learn'}</h1><p className="text-muted-foreground text-sm mt-1">Set up your learning profile.</p></div>
        <div className="bg-card border border-border rounded-2xl p-6 space-y-6">
          <div><Label>Your Class</Label><Select value={activeForm.class_level} onValueChange={(value) => setForm({ ...activeForm, class_level: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{CLASSES.map((item) => <SelectItem key={item} value={item}>Class {item}</SelectItem>)}</SelectContent></Select></div>
          <div><Label>Learning Needs</Label><div className="grid gap-2 mt-2">{DISABILITY_OPTIONS.map((option) => { const selected = activeForm.disability_types.includes(option.id); return <button key={option.id} onClick={() => toggleDisability(option.id)} className={`flex items-center gap-3 p-3 rounded-xl border-2 text-left ${selected ? option.color : 'border-border bg-muted/30'}`}><option.icon className="w-5 h-5" /><span className="text-sm font-medium">{option.label}</span>{selected && <span className="ml-auto text-xs">Selected</span>}</button>; })}</div></div>
          <div><Label>Content Level</Label><div className="grid grid-cols-3 gap-2">{IQ_LEVELS.map((level) => <button key={level} onClick={() => setForm({ ...activeForm, iq_level: level })} className={`p-3 rounded-xl border-2 capitalize ${activeForm.iq_level === level ? 'border-primary bg-accent' : 'border-border bg-muted/30'}`}>{level}</button>)}</div></div>
          <div className="flex gap-3"><Button className="flex-1" onClick={() => saveMutation.mutate(activeForm)}>Save & Start Learning</Button>{profile && <Button variant="outline" onClick={() => setSetupMode(false)}>Cancel</Button>}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8"><div><h1 className="font-poppins font-bold text-2xl">Welcome back{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}</h1><p className="text-muted-foreground text-sm mt-1">Class {profile.class_level} · {profile.iq_level} level</p></div><Button variant="outline" size="sm" onClick={() => { setForm({ class_level: profile.class_level, disability_types: profile.disability_types || [], iq_level: profile.iq_level }); setSetupMode(true); }}><Settings className="w-4 h-4 mr-1" />Edit Profile</Button></div>
      <div className="grid grid-cols-3 gap-4 mb-8">{[{ label: 'Lessons Taken', value: assessments.length, icon: BookOpen }, { label: 'Avg Score', value: `${avgScore}%`, icon: BarChart3 }, { label: 'Level', value: profile.iq_level, icon: Zap }].map((stat) => <div key={stat.label} className="bg-card border border-border rounded-2xl p-4 text-center"><stat.icon className="w-5 h-5 mx-auto mb-2 text-primary" /><p className="font-poppins font-bold text-xl capitalize">{stat.value}</p><p className="text-xs text-muted-foreground">{stat.label}</p></div>)}</div>
      <div className="grid md:grid-cols-3 gap-4">{[{ title: 'Start a Lesson', desc: 'Pick subject & chapter', icon: BookOpen, path: '/student/lessons' }, { title: 'Take Assessment', desc: 'Quizzes, flashcards & puzzles', icon: Brain, path: '/student/assessments' }, { title: 'My Progress', desc: 'View scores and feedback', icon: BarChart3, path: '/student/progress' }].map((card) => <Link key={card.path} to={card.path} className="bg-card border border-border rounded-2xl p-6 hover:shadow-md"><card.icon className="w-7 h-7 text-primary mb-4" /><h3 className="font-semibold mb-1">{card.title}</h3><p className="text-xs text-muted-foreground mb-3">{card.desc}</p><span className="flex items-center gap-1 text-primary text-xs font-medium">Go <ArrowRight className="w-3 h-3" /></span></Link>)}</div>
      <div className="mt-6 bg-card border border-border rounded-2xl p-6">
        <h2 className="font-semibold mb-1">Accessibility Preferences</h2>
        <p className="text-xs text-muted-foreground mb-4">Saved on this computer for a calmer learning experience.</p>
        <div className="grid md:grid-cols-3 gap-3">
          {[
            { key: 'readingSpeed', label: 'Reading Speed', values: ['slow', 'normal'] },
            { key: 'motion', label: 'Motion', values: ['on', 'reduced'] },
            { key: 'contrast', label: 'Contrast', values: ['soft', 'high'] },
          ].map((group) => (
            <div key={group.key}>
              <p className="text-xs font-medium mb-2">{group.label}</p>
              <div className="flex gap-2">
                {group.values.map((value) => (
                  <button key={value} onClick={() => savePrefs({ ...prefs, [group.key]: value })} className={`px-3 py-2 rounded-xl border text-xs capitalize ${prefs[group.key] === value ? 'bg-primary text-white border-primary' : 'bg-background border-border'}`}>{value}</button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <DeleteAccountModal />
    </div>
  );
}

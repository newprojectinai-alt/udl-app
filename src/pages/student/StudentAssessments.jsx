import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { assessmentService, studentService, textbookService } from '@/services/entityService';
import { generateAssessment } from '@/services/aiService';
import { useQuery } from '@tanstack/react-query';
import { Atom, Binary, BookOpen, Brain, Calculator, FlaskConical, Layers, Puzzle, RefreshCw, Sparkles, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/lib/AuthContext';
import { toast } from 'sonner';

const TYPES = [
  { id: 'quiz', label: 'Quiz', icon: Brain, color: 'from-blue-500 to-indigo-600', hint: 'Answer and learn' },
  { id: 'flashcard', label: 'Flashcards', icon: Layers, color: 'from-emerald-500 to-teal-600', hint: 'Flip and remember' },
  { id: 'puzzle', label: 'Puzzle', icon: Puzzle, color: 'from-amber-400 to-orange-500', hint: 'Solve clues' },
];
const CLASSES = ['5', '6', '7', '8', '9', '10'];

export default function StudentAssessments() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedType, setSelectedType] = useState('quiz');
  const [chapter, setChapter] = useState(searchParams.get('chapter') || '');
  const [subject, setSubject] = useState(searchParams.get('subject') || '');
  const [classLevel, setClassLevel] = useState(searchParams.get('class') || '');
  const [loading, setLoading] = useState(false);
  const { data: profiles = [] } = useQuery({ queryKey: ['myProfile', user?.email], queryFn: () => studentService.filter({ user_email: user.email }), enabled: !!user?.email });
  const { data: textbooks = [] } = useQuery({ queryKey: ['readyTextbooks'], queryFn: () => textbookService.filter({ status: 'ready' }) });
  const profile = profiles[0];
  const activeClass = classLevel || profile?.class_level || '';
  const subjects = [...new Set(textbooks.filter((item) => !activeClass || item.class_level === activeClass).map((item) => item.subject))];
  const chapters = textbooks.find((item) => item.subject === subject && item.class_level === activeClass)?.chapters || [];
  const selected = TYPES.find((item) => item.id === selectedType) || TYPES[0];

  const handleGenerate = async () => {
    if (!activeClass || !subject || !chapter) return toast.error('Select class, subject & chapter');
    setLoading(true);
    try {
      const iqLevel = profile?.iq_level || 'standard';
      const result = await generateAssessment({ classLevel: activeClass, subject, chapter, assessmentType: selectedType, iqLevel });
      const assessment = await assessmentService.create({
        student_email: user.email,
        class_level: activeClass,
        subject,
        chapter,
        assessment_type: selectedType,
        iq_level: iqLevel,
        questions: result.questions,
        total_questions: result.questions.length,
        completed: false,
      });
      navigate(`/student/assessment/${assessment.id}`);
    } catch (error) {
      toast.error(error.message || 'Could not generate assessment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen edu-animated-bg p-6 md:p-8">
      <div className="edu-grid-overlay" />
      <FloatingLearningObjects />
      <div className="relative z-10 max-w-4xl mx-auto">
        <div className={`motion-pop mb-8 rounded-3xl bg-gradient-to-r ${selected.color} p-6 text-white shadow-2xl shadow-blue-500/20`}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center">
              <selected.icon className="w-8 h-8" />
            </div>
            <div>
              <p className="text-white/80 text-sm font-medium">Learning checkpoint</p>
              <h1 className="font-poppins font-bold text-3xl">Assessments</h1>
              <p className="text-white/90 text-sm mt-1">Choose a fun activity and check what you understood today.</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          {TYPES.map((type) => (
            <button key={type.id} onClick={() => setSelectedType(type.id)} className={`neon-card ${selectedType === type.id ? 'neon-card-active' : ''} relative overflow-hidden p-[2px] rounded-3xl text-left transition-all hover:-translate-y-1 hover:shadow-xl ${selectedType === type.id ? 'shadow-xl scale-[1.02]' : ''}`}>
              <div className={`absolute inset-0 bg-gradient-to-br ${type.color} ${selectedType === type.id ? 'opacity-100' : 'opacity-10'}`} />
              <div className={`relative rounded-[1.35rem] p-5 h-full ${selectedType === type.id ? 'bg-transparent' : 'bg-white/80 backdrop-blur'}`}>
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-4 ${selectedType === type.id ? 'bg-white/20 text-white' : 'bg-white text-primary shadow-sm'}`}>
                  <type.icon className="w-6 h-6" />
                </div>
                <p className={`text-base font-bold ${selectedType === type.id ? 'text-white' : 'text-foreground'}`}>{type.label}</p>
                <p className={`text-xs mt-1 ${selectedType === type.id ? 'text-white/80' : 'text-muted-foreground'}`}>{type.hint}</p>
              </div>
            </button>
          ))}
        </div>

        <div className="motion-pop bg-white/90 backdrop-blur-xl border border-white/70 rounded-3xl p-6 space-y-5 shadow-2xl shadow-blue-500/10">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Class</label>
              <Select value={activeClass} onValueChange={(value) => { setClassLevel(value); setSubject(''); setChapter(''); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{CLASSES.map((item) => <SelectItem key={item} value={item}>Class {item}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Subject</label>
              <Select value={subject} onValueChange={(value) => { setSubject(value); setChapter(''); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{subjects.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">Chapter</label>
            <Select value={chapter} onValueChange={setChapter} disabled={!subject}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{chapters.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
            </Select>
            <Input value={chapter} onChange={(event) => setChapter(event.target.value)} placeholder="Or type a topic..." className="mt-2" />
          </div>

          <div className="rounded-2xl bg-gradient-to-r from-blue-50 to-emerald-50 border border-blue-100 p-4 flex gap-3">
            <Wand2 className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-foreground">Ready for a fresh challenge?</p>
              <p className="text-xs text-muted-foreground mt-1">Each click creates a new set of questions and puzzle clues.</p>
            </div>
          </div>

          <Button onClick={handleGenerate} disabled={loading || !chapter} className={`w-full bg-gradient-to-r ${selected.color} hover:opacity-95 text-white shadow-lg`} size="lg">
            {loading ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Generating…</> : <><Sparkles className="w-4 h-4 mr-2" />Generate {selected.label}</>}
          </Button>
        </div>
      </div>
    </div>
  );
}

function FloatingLearningObjects() {
  const items = [
    { Icon: Calculator, className: 'top-28 left-8 text-blue-600', label: '÷' },
    { Icon: FlaskConical, className: 'top-20 right-14 text-emerald-600', label: 'science' },
    { Icon: Atom, className: 'bottom-28 left-12 text-violet-600', label: 'atom' },
    { Icon: BookOpen, className: 'bottom-20 right-10 text-orange-600', label: 'book' },
    { Icon: Binary, className: 'top-1/2 right-24 text-indigo-600', label: '01' },
  ];

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map(({ Icon, className, label }, index) => (
        <div key={label} className={`edu-float ${className}`} style={{ animationDuration: `${7 + index}s` }}>
          <Icon className="w-7 h-7" />
        </div>
      ))}
    </div>
  );
}

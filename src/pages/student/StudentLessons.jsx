import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { lessonService, studentService, textbookService } from '@/services/entityService';
import { generateLesson } from '@/services/aiService';
import { BookOpen, Brain, Ear, Eye, RefreshCw, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/lib/AuthContext';
import { toast } from 'sonner';

const CLASSES = ['5', '6', '7', '8', '9', '10'];

export default function StudentLessons() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedChapter, setSelectedChapter] = useState('');
  const [loading, setLoading] = useState(false);
  const { data: profiles = [] } = useQuery({ queryKey: ['myProfile', user?.email], queryFn: () => studentService.filter({ user_email: user.email }), enabled: !!user?.email });
  const profile = profiles[0];
  const classLevel = selectedClass || profile?.class_level || '';
  const { data: textbooks = [] } = useQuery({ queryKey: ['textbooks', classLevel, selectedSubject], queryFn: () => textbookService.filter({ status: 'ready' }) });
  const readyTextbooks = textbooks.filter((item) => item.status === 'ready');
  const availableClasses = [...new Set(readyTextbooks.map((item) => item.class_level))].sort();
  const visibleClass = classLevel || availableClasses[0] || '';
  const subjects = [...new Set(readyTextbooks.filter((item) => !visibleClass || item.class_level === visibleClass).map((item) => item.subject))];
  const matchingTextbooks = readyTextbooks.filter((item) => item.subject === selectedSubject && item.class_level === visibleClass);
  const chapters = [...new Set(matchingTextbooks.flatMap((item) => item.chapters || []))];
  const selectedTextbook = matchingTextbooks.find((item) => (item.chapters || []).includes(selectedChapter)) || matchingTextbooks[0];

  const handleStartLesson = async () => {
    if (!visibleClass || !selectedSubject || !selectedChapter) return toast.error('Please select class, subject, and chapter');
    setLoading(true);
    const iqLevel = profile?.iq_level || 'standard';
    const existing = await lessonService.filter({ class_level: visibleClass, subject: selectedSubject, chapter: selectedChapter, iq_level: iqLevel });
    const lesson = existing[0] || await lessonService.create({ textbook_id: selectedTextbook?.id || '', chapter: selectedChapter, class_level: visibleClass, subject: selectedSubject, iq_level: iqLevel, ...(await generateLesson({ classLevel: visibleClass, subject: selectedSubject, chapter: selectedChapter, iqLevel, disabilities: profile?.disability_types || [] })) });
    setLoading(false);
    navigate(`/student/lesson/${lesson.id}?class=${visibleClass}&subject=${selectedSubject}&chapter=${encodeURIComponent(selectedChapter)}`);
  };

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto"><div className="mb-8"><h1 className="font-poppins font-bold text-2xl">Choose Your Lesson</h1><p className="text-muted-foreground text-sm mt-1">Select a class, subject, and chapter.</p></div>
      <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
        <div><label className="text-sm font-medium">Class</label><Select value={visibleClass} onValueChange={(value) => { setSelectedClass(value); setSelectedSubject(''); setSelectedChapter(''); }}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{CLASSES.map((item) => <SelectItem key={item} value={item}>Class {item}</SelectItem>)}</SelectContent></Select>{availableClasses.length > 0 && <p className="text-xs text-muted-foreground mt-1">Available uploaded classes: {availableClasses.join(', ')}</p>}</div>
        <div><label className="text-sm font-medium">Subject</label><Select value={selectedSubject} onValueChange={(value) => { setSelectedSubject(value); setSelectedChapter(''); }} disabled={!visibleClass}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{subjects.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select>{visibleClass && subjects.length === 0 && <p className="text-xs text-amber-600 mt-1">No ready textbooks found for Class {visibleClass}. Upload one as admin or choose a class listed above.</p>}</div>
        <div><label className="text-sm font-medium">Chapter</label><Select value={selectedChapter} onValueChange={setSelectedChapter} disabled={!selectedSubject}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{chapters.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>
        {profile && <div className="bg-accent/50 rounded-xl p-4"><p className="text-xs font-semibold mb-2">Your lesson will be adapted for:</p><div className="flex flex-wrap gap-2"><span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full capitalize">{profile.iq_level}</span>{(profile.disability_types || []).map((item) => <span key={item} className="text-xs px-2 py-1 bg-secondary/20 text-secondary rounded-full flex items-center gap-1 capitalize">{item === 'visual' && <Eye className="w-3 h-3" />}{item === 'hearing' && <Ear className="w-3 h-3" />}{item === 'cognitive' && <Brain className="w-3 h-3" />}{item}</span>)}</div></div>}
        <Button onClick={handleStartLesson} disabled={loading || !selectedChapter} className="w-full" size="lg">{loading ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Generating…</> : <><Sparkles className="w-4 h-4 mr-2" />Start AI Lesson</>}</Button>
      </div>
      <div className="mt-6 bg-card border border-border rounded-2xl p-5">
        <p className="text-sm font-medium mb-3">Ready textbooks visible to students</p>
        {readyTextbooks.length === 0 ? (
          <p className="text-sm text-muted-foreground">No ready textbooks found yet. Upload and process a PDF from the admin dashboard.</p>
        ) : (
          <div className="space-y-2">
            {readyTextbooks.map((textbook) => (
              <div key={textbook.id} className="text-sm flex items-center justify-between border border-border rounded-xl p-3">
                <span>{textbook.title}</span>
                <span className="text-xs text-muted-foreground">Class {textbook.class_level} · {textbook.subject} · {textbook.chapters?.length || 0} chapters</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="mt-6 bg-muted/50 rounded-2xl p-5"><div className="flex items-center gap-2 mb-3"><BookOpen className="w-4 h-4 text-muted-foreground" /><p className="text-sm font-medium">How it works</p></div><p className="text-sm text-muted-foreground">AI creates a personalized lesson, then you can take a quiz or flashcard session.</p></div>
    </div>
  );
}

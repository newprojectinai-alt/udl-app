import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { assessmentService } from '@/services/entityService';
import { generateFeedback } from '@/services/aiService';
import { ArrowLeft, Atom, BookOpen, Calculator, CheckCircle, ChevronRight, FlaskConical, HelpCircle, RotateCcw, Trophy, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

const TYPE_STYLE = {
  quiz: { gradient: 'from-blue-500 to-indigo-600', bg: 'from-blue-50 via-white to-indigo-50', emoji: '🧠', title: 'Quiz Quest' },
  flashcard: { gradient: 'from-emerald-500 to-teal-600', bg: 'from-emerald-50 via-white to-teal-50', emoji: '🃏', title: 'Flashcard Sprint' },
  puzzle: { gradient: 'from-amber-400 to-orange-500', bg: 'from-amber-50 via-white to-orange-50', emoji: '🧩', title: 'Puzzle Mission' },
};

export default function AssessmentSession() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState({});
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const [sequenceDraft, setSequenceDraft] = useState([]);
  const [blankDraft, setBlankDraft] = useState('');
  const [startTime] = useState(Date.now());
  const [aiFeedback, setAiFeedback] = useState('');
  const { data: assessment, isLoading } = useQuery({ queryKey: ['assessment', assessmentId], queryFn: async () => (await assessmentService.filter({ id: assessmentId }))[0], enabled: !!assessmentId });
  const saveMutation = useMutation({ mutationFn: (data) => assessmentService.update(assessmentId, data) });

  if (isLoading) return <div className="p-8">Loading assessment…</div>;
  if (!assessment) return <div className="p-8 text-center text-muted-foreground">Assessment not found</div>;

  const style = TYPE_STYLE[assessment.assessment_type] || TYPE_STYLE.quiz;
  const questions = assessment.questions || [];
  const question = questions[currentQ];
  const score = questions.filter((item, index) => answers[index] === item.correct_answer).length;
  const percentage = questions.length ? Math.round((score / questions.length) * 100) : 0;
  const progress = questions.length ? ((currentQ + 1) / questions.length) * 100 : 0;

  const handleFinish = async () => {
    const feedback = await generateFeedback({ assessment, score, totalQuestions: questions.length, percentage });
    await saveMutation.mutateAsync({
      questions: questions.map((item, index) => ({ ...item, student_answer: answers[index] || '', is_correct: answers[index] === item.correct_answer })),
      score,
      time_spent_seconds: Math.floor((Date.now() - startTime) / 1000),
      completed: true,
      ai_feedback: feedback,
    });
    setAiFeedback(feedback);
    setFinished(true);
  };

  const handleNext = () => {
    setRevealed(false);
    setSequenceDraft([]);
    setBlankDraft('');
    currentQ < questions.length - 1 ? setCurrentQ(currentQ + 1) : handleFinish();
  };

  if (finished) {
    return (
      <div className="min-h-screen edu-animated-bg p-6 md:p-8">
        <div className="edu-grid-overlay" />
        <FloatingSessionObjects />
        <div className="relative z-10 max-w-2xl mx-auto text-center motion-pop">
          <div className={`mx-auto mb-5 w-24 h-24 rounded-full bg-gradient-to-br ${style.gradient} text-white flex items-center justify-center shadow-xl`}>
            <Trophy className="w-12 h-12" />
          </div>
          <h1 className="font-poppins font-bold text-3xl mb-2">{percentage >= 80 ? 'Amazing work!' : percentage >= 60 ? 'Good job!' : 'Keep practicing!'}</h1>
          <p className="text-muted-foreground mb-6">{assessment.chapter} · {assessment.subject}</p>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <ScoreCard label="Score" value={`${percentage}%`} color="text-blue-600" />
            <ScoreCard label="Correct" value={score} color="text-emerald-600" />
            <ScoreCard label="Try Again" value={questions.length - score} color="text-orange-500" />
          </div>
          <div className="bg-white/90 border rounded-3xl p-5 mb-6 text-left shadow-sm">
            <p className="text-xs font-semibold mb-2 text-primary">AI Feedback</p>
            <p className="text-sm">{aiFeedback}</p>
          </div>
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={() => navigate('/student/assessments')}><RotateCcw className="w-4 h-4 mr-2" />New Assessment</Button>
            <Button onClick={() => navigate('/student/progress')}>View Progress</Button>
          </div>
        </div>
      </div>
    );
  }

  if (assessment.assessment_type === 'flashcard') {
    return (
      <AssessmentShell style={style} assessment={assessment} currentQ={currentQ} questions={questions} progress={progress} navigate={navigate}>
        <div className="neon-card neon-card-active rounded-3xl p-[2px] shadow-2xl shadow-emerald-500/20">
        <div className="relative bg-white/90 border-2 border-white/70 rounded-[1.35rem] p-8 min-h-64 flex items-center justify-center text-center">
          <div>
            <p className="text-xs text-muted-foreground mb-3">FLASHCARD</p>
            <p className="font-poppins font-semibold text-xl">{question?.question}</p>
            <p className="text-primary font-semibold mt-5">{question?.correct_answer}</p>
          </div>
        </div>
        </div>
        <div className="flex gap-3 mt-8">
          <Button variant="outline" onClick={handleNext} className="flex-1">Still learning</Button>
          <Button onClick={() => { setAnswers({ ...answers, [currentQ]: question?.correct_answer }); handleNext(); }} className={`flex-1 bg-gradient-to-r ${style.gradient} text-white`}>Got it</Button>
        </div>
      </AssessmentShell>
    );
  }

  if (assessment.assessment_type === 'puzzle' && question?.question_type === 'sequence') {
    const remaining = (question.options || []).filter((option) => !sequenceDraft.includes(option));
    const draftAnswer = sequenceDraft.join(' → ');
    return (
      <AssessmentShell style={style} assessment={assessment} currentQ={currentQ} questions={questions} progress={progress} navigate={navigate}>
        <PuzzleQuestionCard style={style} question={question} />
        <div className="bg-white/90 border rounded-3xl p-5 shadow-sm">
          <p className="text-xs font-semibold text-muted-foreground mb-3">Tap cards in the correct order</p>
          <div className="min-h-16 rounded-2xl bg-blue-50 border border-blue-100 p-3 mb-4 flex flex-wrap gap-2">
            {sequenceDraft.length ? sequenceDraft.map((item, index) => <span key={item} className="px-3 py-2 rounded-xl bg-primary text-white text-sm font-medium">{index + 1}. {item}</span>) : <span className="text-sm text-muted-foreground">Your order will appear here…</span>}
          </div>
          <div className="grid sm:grid-cols-2 gap-2">
            {remaining.map((option) => <button key={option} onClick={() => setSequenceDraft([...sequenceDraft, option])} disabled={revealed} className="p-3 rounded-2xl border bg-white hover:border-primary text-sm text-left">{option}</button>)}
          </div>
          <div className="flex gap-2 mt-4">
            <Button variant="outline" onClick={() => setSequenceDraft([])} disabled={revealed}>Reset order</Button>
            <Button className={`flex-1 bg-gradient-to-r ${style.gradient} text-white`} disabled={revealed || sequenceDraft.length !== (question.options || []).length} onClick={() => { setAnswers({ ...answers, [currentQ]: draftAnswer }); setRevealed(true); }}>
              Check Sequence
            </Button>
          </div>
          {revealed && <FeedbackStrip correct={draftAnswer === question.correct_answer} correctAnswer={question.correct_answer} />}
        </div>
        {revealed && <Button onClick={handleNext} className={`w-full mt-5 bg-gradient-to-r ${style.gradient} text-white shadow-lg`}>{currentQ < questions.length - 1 ? 'Next Puzzle' : 'See Results'}</Button>}
      </AssessmentShell>
    );
  }

  if (assessment.assessment_type === 'puzzle' && question?.question_type === 'fill_blank') {
    const selectedAnswer = answers[currentQ] || blankDraft;
    return (
      <AssessmentShell style={style} assessment={assessment} currentQ={currentQ} questions={questions} progress={progress} navigate={navigate}>
        <PuzzleQuestionCard style={style} question={question} />
        <div className="bg-white/90 border rounded-3xl p-5 shadow-sm">
          <label className="text-xs font-semibold text-muted-foreground">Type or choose the missing word</label>
          <input value={blankDraft} onChange={(event) => setBlankDraft(event.target.value)} disabled={revealed} className="mt-2 w-full rounded-2xl border border-border px-4 py-3 text-lg font-semibold outline-none focus:ring-2 focus:ring-primary" placeholder="Your answer..." />
          <div className="grid sm:grid-cols-2 gap-2 mt-4">
            {(question.options || []).map((option) => <button key={option} onClick={() => setBlankDraft(option)} disabled={revealed} className="p-3 rounded-2xl border bg-white hover:border-primary text-sm text-left">{option}</button>)}
          </div>
          <Button className={`w-full mt-4 bg-gradient-to-r ${style.gradient} text-white`} disabled={revealed || !blankDraft.trim()} onClick={() => { setAnswers({ ...answers, [currentQ]: blankDraft.trim() }); setRevealed(true); }}>
            Check Answer
          </Button>
          {revealed && <FeedbackStrip correct={selectedAnswer === question.correct_answer} correctAnswer={question.correct_answer} />}
        </div>
        {revealed && <Button onClick={handleNext} className={`w-full mt-5 bg-gradient-to-r ${style.gradient} text-white shadow-lg`}>{currentQ < questions.length - 1 ? 'Next Puzzle' : 'See Results'}</Button>}
      </AssessmentShell>
    );
  }

  return (
    <AssessmentShell style={style} assessment={assessment} currentQ={currentQ} questions={questions} progress={progress} navigate={navigate}>
      <PuzzleQuestionCard style={style} question={question} />
      <div className="space-y-3">
        {(question?.options || []).map((option, index) => {
          const selected = answers[currentQ] === option;
          const correct = revealed && option === question.correct_answer;
          const wrong = revealed && selected && option !== question.correct_answer;
          return (
            <button key={`${option}-${index}`} onClick={() => { if (!revealed) { setAnswers({ ...answers, [currentQ]: option }); setRevealed(true); } }} disabled={revealed} className={`w-full text-left p-4 rounded-2xl border-2 transition-all hover:shadow-md ${correct ? 'border-emerald-400 bg-emerald-50' : wrong ? 'border-red-400 bg-red-50' : selected ? 'border-primary bg-accent' : 'border-border bg-white/90 hover:border-primary/50'}`}>
              <div className="flex justify-between gap-3">
                <span><span className="font-bold text-primary mr-2">{String.fromCharCode(65 + index)}.</span>{option}</span>
                {correct && <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />}
                {wrong && <XCircle className="w-5 h-5 text-red-600 shrink-0" />}
              </div>
            </button>
          );
        })}
      </div>
      {revealed && <Button onClick={handleNext} className={`w-full mt-5 bg-gradient-to-r ${style.gradient} text-white shadow-lg`}>{currentQ < questions.length - 1 ? <><ChevronRight className="w-4 h-4 mr-1" />Next Question</> : 'See Results'}</Button>}
    </AssessmentShell>
  );
}

function PuzzleQuestionCard({ style, question }) {
  return (
    <div className="bg-white/90 border rounded-3xl p-6 mb-5 shadow-sm">
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-2xl bg-gradient-to-br ${style.gradient} text-white flex items-center justify-center shrink-0`}>
          <HelpCircle className="w-5 h-5" />
        </div>
        <div>
          <p className="font-poppins font-semibold text-lg leading-relaxed">{question?.question}</p>
          {question?.hint && <p className="text-xs text-muted-foreground mt-2">Hint: {question.hint}</p>}
        </div>
      </div>
    </div>
  );
}

function FeedbackStrip({ correct, correctAnswer }) {
  return (
    <div className={`mt-4 rounded-2xl p-3 text-sm ${correct ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
      {correct ? 'Correct! Nice puzzle solving.' : `Not quite. Correct answer: ${correctAnswer}`}
    </div>
  );
}

function AssessmentShell({ style, assessment, currentQ, questions, progress, navigate, children }) {
  return (
    <div className="min-h-screen edu-animated-bg p-6 md:p-8">
      <div className="edu-grid-overlay" />
      <FloatingSessionObjects />
      <div className="relative z-10 max-w-2xl mx-auto">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-sm text-muted-foreground mb-4"><ArrowLeft className="w-4 h-4" />Back</button>
        <div className={`motion-pop rounded-3xl bg-gradient-to-r ${style.gradient} text-white p-5 mb-5 shadow-2xl shadow-blue-500/20`}>
          <div className="flex justify-between items-start gap-4">
            <div>
              <p className="text-white/80 text-sm">{style.emoji} {style.title}</p>
              <h1 className="font-poppins font-bold text-2xl mt-1">{assessment.chapter}</h1>
              <p className="text-white/80 text-xs mt-1">{assessment.subject} · {assessment.iq_level} level</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">{currentQ + 1}/{questions.length}</p>
              <p className="text-white/80 text-xs">questions</p>
            </div>
          </div>
          <div className="h-2 bg-white/20 rounded-full overflow-hidden mt-5">
            <div className="h-full bg-white transition-all duration-500" style={{ width: `${progress}%` }} />
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

function ScoreCard({ label, value, color }) {
  return (
    <div className="bg-white/90 border rounded-3xl p-4 shadow-sm">
      <p className={`font-bold text-3xl ${color}`}>{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function FloatingSessionObjects() {
  const items = [
    { Icon: Calculator, className: 'top-24 left-8 text-blue-600' },
    { Icon: FlaskConical, className: 'top-32 right-10 text-emerald-600' },
    { Icon: Atom, className: 'bottom-24 left-10 text-violet-600' },
    { Icon: BookOpen, className: 'bottom-20 right-12 text-orange-600' },
  ];

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map(({ Icon, className }, index) => (
        <div key={index} className={`edu-float ${className}`} style={{ animationDuration: `${7 + index}s` }}>
          <Icon className="w-7 h-7" />
        </div>
      ))}
    </div>
  );
}

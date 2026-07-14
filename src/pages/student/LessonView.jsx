import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { lessonService, studentService } from '@/services/entityService';
import { resolveApiUrl, USE_BACKEND } from '@/services/apiClient';
import { backendVideoService } from '@/services/backendServices';
import { ArrowLeft, BookOpen, Brain, ChevronLeft, ChevronRight, Ear, Eye, Lightbulb, MessageSquare, PauseCircle, PlayCircle, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/AuthContext';

const VIDEO_RENDERER = 'cogvideo';

export default function LessonView() {
  const { lessonId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('lesson');
  const [speaking, setSpeaking] = useState(false);
  const [speechRate, setSpeechRate] = useState(0.9);
  const [displayLevel, setDisplayLevel] = useState('standard');
  const [videoJob, setVideoJob] = useState(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [renderLoading, setRenderLoading] = useState(false);
  const [videoError, setVideoError] = useState('');
  const { data: profiles = [] } = useQuery({ queryKey: ['myProfile', user?.email], queryFn: () => studentService.filter({ user_email: user.email }), enabled: !!user?.email });
  const profile = profiles[0];
  const { data: lesson, isLoading } = useQuery({ queryKey: ['lesson', lessonId], queryFn: async () => (await lessonService.filter({ id: lessonId }))[0], enabled: !!lessonId });

  useEffect(() => {
    if (!USE_BACKEND || !lesson?.id) return undefined;

    let cancelled = false;
    const loadLatestVideo = async () => {
      try {
        const latest = await backendVideoService.latestForLesson(lesson.id);
        if (!cancelled && latest?.id) {
          setVideoJob(latest);
          setRenderLoading(latest.status === 'rendering');
        }
      } catch (error) {
        if (!cancelled) setVideoError(error.message || 'Could not load existing video');
      }
    };

    loadLatestVideo();
    return () => {
      cancelled = true;
    };
  }, [lesson?.id]);

  useEffect(() => {
    if (!USE_BACKEND || !videoJob?.id || videoJob.status !== 'rendering') return undefined;

    const timer = setInterval(async () => {
      try {
        const latest = await backendVideoService.get(videoJob.id);
        setVideoJob(latest);
        if (latest.video_url || latest.status === 'completed' || latest.status === 'failed') {
          setRenderLoading(false);
        }
      } catch (error) {
        setVideoError(error.message || 'Could not refresh video status');
        setRenderLoading(false);
      }
    }, 5000);

    return () => clearInterval(timer);
  }, [videoJob?.id, videoJob?.status]);

  const speak = (text) => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text || '');
    utterance.rate = speechRate;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };
  const stopSpeaking = () => {
    window.speechSynthesis.cancel();
    setSpeaking(false);
  };
  if (isLoading) return <div className="p-8">Loading lesson…</div>;
  if (!lesson) return <div className="p-8 text-center text-muted-foreground">Lesson not found</div>;
  const hasVisual = profile?.disability_types?.includes('visual');
  const hasHearing = profile?.disability_types?.includes('hearing');
  const lessonAnimationType = lesson.animation_type || inferAnimationType(lesson);
  const animationScenes = (lesson.animation_script?.length ? lesson.animation_script : buildFallbackAnimation(lesson))
    .map((scene) => ({ ...scene, animation_type: scene.animation_type || lessonAnimationType }));
  const tabs = [{ id: 'lesson', label: 'Lesson', icon: BookOpen }, { id: 'animation', label: 'Animated Explanation', icon: PlayCircle }, { id: 'keypoints', label: 'Key Points', icon: Lightbulb }, { id: 'vocab', label: 'Vocabulary', icon: Brain }, { id: 'captions', label: 'Captions', icon: MessageSquare }, ...(hasVisual ? [{ id: 'visual', label: 'Visual Aid', icon: Eye }] : [])];
  const handleGenerateVideo = async () => {
    if (!USE_BACKEND) {
      setVideoJob({
        status: 'storyboard_ready',
        scenes: animationScenes,
        captions: animationScenes.map((scene, index) => ({ scene_number: index + 1, text: scene.caption })),
        provider_metadata: { renderer: 'local_preview' },
      });
      return;
    }
    setVideoLoading(true);
    setVideoError('');
    try {
      const job = await backendVideoService.generate(lesson.id, { renderer: VIDEO_RENDERER });
      setVideoJob(job);
    } catch (error) {
      setVideoError(error.message || 'Failed to prepare video');
    } finally {
      setVideoLoading(false);
    }
  };
  const handleRenderVideo = async () => {
    if (!videoJob?.id || !USE_BACKEND) return;
    setRenderLoading(true);
    setVideoError('');
    try {
      const queued = await backendVideoService.render(videoJob.id);
      setVideoJob(queued);
      if (queued.video_url || queued.status === 'completed' || queued.status === 'failed') {
        setRenderLoading(false);
      }
    } catch (error) {
      setVideoError(error.message || 'Failed to render MP4');
      try {
        const latest = await backendVideoService.get(videoJob.id);
        setVideoJob(latest);
      } catch {}
    }
  };
  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8"><button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3"><ArrowLeft className="w-4 h-4" />Back</button><div className="flex items-center gap-2 text-sm text-muted-foreground mb-2"><BookOpen className="w-4 h-4" />Class {searchParams.get('class')}<ChevronRight className="w-3 h-3" />{searchParams.get('subject')}<ChevronRight className="w-3 h-3" />{searchParams.get('chapter')}</div><div className="flex items-center justify-between mb-4"><h1 className="font-poppins font-bold text-xl">{lesson.chapter}</h1><span className="text-xs px-3 py-1 rounded-full bg-blue-50 text-blue-700 capitalize">{displayLevel} level</span></div><div className="flex gap-2 mb-4 flex-wrap">{hasVisual && <span className="flex items-center gap-1 text-xs px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full"><Eye className="w-3 h-3" />Visual support</span>}{hasHearing && <span className="flex items-center gap-1 text-xs px-2.5 py-1 bg-violet-50 text-violet-700 rounded-full"><Ear className="w-3 h-3" />Hearing support</span>}<span className="flex items-center gap-1 text-xs px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-full"><Volume2 className="w-3 h-3" />Read aloud</span></div>
      <div className="bg-card border border-border rounded-2xl p-4 mb-5">
        <p className="text-sm font-semibold mb-3">Accessibility Controls</p>
        <div className="grid md:grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-muted-foreground">Speed</label>
            <div className="flex gap-2 mt-1">
              <button onClick={() => setSpeechRate(0.7)} className={`px-3 py-2 text-sm rounded-xl border ${speechRate === 0.7 ? 'bg-primary text-primary-foreground' : 'bg-background'}`}>Slow</button>
              <button onClick={() => setSpeechRate(0.95)} className={`px-3 py-2 text-sm rounded-xl border ${speechRate === 0.95 ? 'bg-primary text-primary-foreground' : 'bg-background'}`}>Normal</button>
            </div>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Level</label>
            <div className="flex gap-2 mt-1 flex-wrap">
              {['basic', 'standard', 'advanced'].map((level) => <button key={level} onClick={() => setDisplayLevel(level)} className={`px-3 py-2 text-sm rounded-xl border capitalize ${displayLevel === level ? 'bg-primary text-primary-foreground' : 'bg-background'}`}>{level}</button>)}
            </div>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Read Aloud</label>
            <div className="flex gap-2 mt-1">
              <Button variant="outline" size="sm" onClick={() => speaking ? stopSpeaking() : speak(getReadableText(activeTab, lesson, animationScenes))}><Volume2 className="w-4 h-4 mr-1" />{speaking ? 'Stop' : 'Read'}</Button>
            </div>
          </div>
        </div>
      </div>
      <div className="flex gap-1 bg-muted p-1 rounded-xl mb-6 overflow-x-auto">{tabs.map((tab) => <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm ${activeTab === tab.id ? 'bg-card shadow-sm' : 'text-muted-foreground'}`}><tab.icon className="w-3.5 h-3.5" />{tab.label}</button>)}</div>
      <div className="bg-card border border-border rounded-2xl p-6">{activeTab === 'lesson' && <><div className="flex justify-between mb-4"><h2 className="font-semibold">Lesson Content</h2><Button variant="outline" size="sm" onClick={() => speaking ? stopSpeaking() : speak(lesson.content_text)}><Volume2 className="w-4 h-4 mr-1" />{speaking ? 'Stop' : 'Read Aloud'}</Button></div><p className="whitespace-pre-wrap text-sm leading-relaxed">{adaptTextForLevel(lesson.content_text, displayLevel)}</p></>}{activeTab === 'animation' && <AnimatedExplanation scenes={animationScenes} speak={speak} speaking={speaking} stopSpeaking={stopSpeaking} displayLevel={displayLevel} />}{activeTab === 'keypoints' && <div className="space-y-3">{lesson.key_points?.map((point, index) => <div key={index} className="flex gap-3 p-3 bg-accent/40 rounded-xl"><span className="w-6 h-6 bg-primary text-white rounded-full text-xs flex items-center justify-center">{index + 1}</span><p className="text-sm">{adaptTextForLevel(point, displayLevel)}</p></div>)}</div>}{activeTab === 'vocab' && <div className="space-y-3">{lesson.vocabulary?.map((item) => <div key={item.word} className="p-3 border border-border rounded-xl"><p className="font-semibold text-sm">{item.word}</p><p className="text-sm text-muted-foreground">{item.definition}</p></div>)}</div>}{activeTab === 'captions' && <div><h2 className="font-semibold mb-3">Captions</h2><p className="text-sm leading-relaxed whitespace-pre-wrap">{lesson.caption_text || animationScenes.map((scene) => scene.caption).join('\n\n')}</p></div>}{activeTab === 'visual' && <p className="text-sm leading-relaxed">{lesson.visual_description}</p>}</div>
      <VideoPipelinePanel videoJob={videoJob} loading={videoLoading} renderLoading={renderLoading} error={videoError} onGenerate={handleGenerateVideo} onRender={handleRenderVideo} />
      <Button className="mt-6" onClick={() => navigate(`/student/assessments?class=${lesson.class_level}&subject=${lesson.subject}&chapter=${encodeURIComponent(lesson.chapter)}`)}>Take Assessment</Button>
    </div>
  );
}

function AnimatedExplanation({ scenes, speak, speaking, stopSpeaking, displayLevel }) {
  const [activeScene, setActiveScene] = useState(0);
  const [playing, setPlaying] = useState(false);
  const scene = scenes[activeScene] || scenes[0];
  const progress = scenes.length ? ((activeScene + 1) / scenes.length) * 100 : 0;

  useEffect(() => {
    if (!playing || scenes.length <= 1) return undefined;
    const timer = setTimeout(() => {
      setActiveScene((current) => {
        if (current >= scenes.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 5500);
    return () => clearTimeout(timer);
  }, [activeScene, playing, scenes.length]);

  const goPrevious = () => {
    setPlaying(false);
    setActiveScene((current) => Math.max(0, current - 1));
  };

  const goNext = () => {
    setPlaying(false);
    setActiveScene((current) => Math.min(scenes.length - 1, current + 1));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-semibold">Animated Explanation</h2>
          <p className="text-xs text-muted-foreground">Scene-by-scene visual explanation with captions and narration.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => speaking ? stopSpeaking() : speak(scene.narration || scene.caption)}>
          <Volume2 className="w-4 h-4 mr-1" />{speaking ? 'Stop Voice' : 'Read Scene'}
        </Button>
      </div>

      <div className="rounded-2xl border border-border overflow-hidden bg-background">
        <div className="h-2 bg-muted">
          <div className="h-full bg-primary transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
        <div className="min-h-64 bg-gradient-to-br from-blue-50 via-white to-emerald-50 flex items-center justify-center p-6">
          <div className="relative w-full max-w-xl text-center">
            <ConceptAnimation scene={scene} sceneIndex={activeScene} playing={playing} animationType={scene.animation_type} />
            <div className="bg-white/80 backdrop-blur border border-border rounded-2xl p-4 shadow-sm">
              <p className="text-xs text-muted-foreground mb-1">Scene {activeScene + 1} of {scenes.length}</p>
              <h3 className="font-poppins font-semibold text-lg mb-2">{scene.title}</h3>
              <p className="text-sm text-foreground">{adaptTextForLevel(scene.caption, displayLevel)}</p>
            </div>
          </div>
        </div>
        <div className="p-5">
          <p className="text-xs text-muted-foreground mb-4">Visual: {scene.visual}</p>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={goPrevious} disabled={activeScene === 0}>
                <ChevronLeft className="w-4 h-4 mr-1" />Previous
              </Button>
              <Button size="sm" onClick={() => setPlaying((value) => !value)}>
                {playing ? <PauseCircle className="w-4 h-4 mr-1" /> : <PlayCircle className="w-4 h-4 mr-1" />}
                {playing ? 'Pause' : 'Play'}
              </Button>
              <Button variant="outline" size="sm" onClick={goNext} disabled={activeScene === scenes.length - 1}>
                Next<ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
            <div className="flex gap-1">
              {scenes.map((_, index) => (
                <button
                  key={index}
                  onClick={() => { setPlaying(false); setActiveScene(index); }}
                  className={`w-2.5 h-2.5 rounded-full ${activeScene === index ? 'bg-primary' : 'bg-muted'}`}
                  aria-label={`Go to scene ${index + 1}`}
                />
              ))}
            </div>
          </div>
          <div className="mt-5 rounded-xl bg-slate-900 text-white p-4">
            <p className="text-xs text-white/60 mb-1">Captions</p>
            <p className="text-sm">{adaptTextForLevel(scene.caption, displayLevel)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function buildFallbackAnimation(lesson) {
  return [
    {
      title: 'Main idea',
      caption: `This lesson explains ${lesson.chapter}.`,
      visual: 'The chapter title appears in the center with connected idea cards.',
      narration: `This lesson explains ${lesson.chapter}.`,
    },
    {
      title: 'Important points',
      caption: lesson.key_points?.[0] || 'We look at the most important ideas step by step.',
      visual: 'Key points appear one by one with simple icons.',
      narration: lesson.key_points?.[0] || 'We look at the most important ideas step by step.',
    },
    {
      title: 'Review',
      caption: 'Now review the idea and try an assessment.',
      visual: 'A check mark and quiz card appear.',
      narration: 'Now review the idea and try an assessment.',
    },
  ];
}

function VideoPipelinePanel({ videoJob, loading, renderLoading, error, onGenerate, onRender }) {
  const progressPercent = Math.min(100, Math.max(0, Number(videoJob?.provider_metadata?.progress_percent || 0)));
  const progressLabel = videoJob?.provider_metadata?.progress_label || '';

  return (
    <div className="mt-6 bg-card border border-border rounded-2xl p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold">MP4 Video Pipeline</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Creates an AI storyboard, narration, captions, and a CogVideoX MP4 using the RunPod GPU backend.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onGenerate} disabled={loading}>
            {loading ? 'Preparing…' : 'Prepare Video'}
          </Button>
          {videoJob?.id && !videoJob.video_url && (
            <Button size="sm" onClick={onRender} disabled={renderLoading || videoJob.status === 'rendering'}>
              {renderLoading || videoJob.status === 'rendering' ? 'Rendering…' : 'Render MP4'}
            </Button>
          )}
        </div>
      </div>

      <div className="mt-5 rounded-2xl bg-gradient-to-r from-blue-50 to-violet-50 border border-blue-100 p-4">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <p className="text-sm font-semibold">CogVideoX AI Video</p>
            <p className="text-xs text-muted-foreground">The backend sends your lesson storyboard to RunPod CogVideoX, validates the MP4, and stores it in S3.</p>
          </div>
          <div className="hidden sm:flex px-3 py-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-semibold shadow-sm">
            AI Video
          </div>
        </div>
        <div className="rounded-2xl bg-white/80 border border-blue-100 p-4">
          <p className="text-sm font-semibold">Production video uses CogVideoX on RunPod</p>
          <p className="text-xs text-muted-foreground mt-1">
            Keep the RunPod pod running and configure `VIDEO_API_ENDPOINT`, `VIDEO_API_TOKEN`, and `VIDEO_API_MODE=async` in the backend.
          </p>
        </div>
      </div>

      {videoJob && (
        <div className="mt-4 space-y-3">
          {error && <div className="rounded-xl bg-red-50 text-red-700 p-3 text-sm">{error}</div>}
          <div className="rounded-xl bg-muted/50 p-3">
            <p className="text-xs text-muted-foreground">Status</p>
            <p className="text-sm font-semibold capitalize">{videoJob.status?.replaceAll('_', ' ')}</p>
            {progressPercent > 0 && (
              <div className="mt-3">
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span>{progressLabel || 'Working...'}</span>
                  <span>{progressPercent}%</span>
                </div>
                <div className="h-2 rounded-full bg-background overflow-hidden border border-border">
                  <div className="h-full bg-primary transition-all duration-500" style={{ width: `${progressPercent}%` }} />
                </div>
              </div>
            )}
            {videoJob.status === 'rendering' && <p className="text-xs text-muted-foreground mt-1">This can take a few minutes. The page will refresh automatically.</p>}
            {videoJob.error_message && <p className="text-xs text-red-600 mt-1">{videoJob.error_message}</p>}
          </div>
          {videoJob.video_url ? (
            <video src={resolveApiUrl(videoJob.video_url)} controls className="w-full rounded-xl border border-border" />
          ) : (
            <div className="rounded-xl border border-dashed border-border p-4">
              <p className="text-sm font-medium mb-2">AI storyboard timeline created</p>
              <p className="text-xs text-muted-foreground">
                Click Render MP4 to generate the final animated learning video.
              </p>
            </div>
          )}
          <div className="grid md:grid-cols-2 gap-3">
            {(videoJob.scenes || []).slice(0, 4).map((scene) => (
              <div key={scene.scene_number || scene.title} className="rounded-xl border border-border p-3">
                <p className="text-xs text-muted-foreground">Scene {scene.scene_number}</p>
                <p className="text-sm font-semibold">{scene.title}</p>
                <p className="text-xs text-muted-foreground mt-1">{scene.caption}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConceptAnimation({ scene, sceneIndex, playing, animationType }) {
  const type = animationType || scene?.animation_type || inferAnimationType({ chapter: scene?.title, content_text: scene?.caption, subject: scene?.visual });
  if (type === 'photosynthesis') return <PhotosynthesisAnimation playing={playing} />;
  if (type === 'food_chain') return <FoodChainAnimation playing={playing} />;
  if (type === 'water_cycle') return <WaterCycleAnimation playing={playing} />;
  if (type === 'states_of_matter') return <StatesOfMatterAnimation playing={playing} />;
  if (type === 'electric_circuit') return <ElectricCircuitAnimation playing={playing} />;
  if (type === 'fractions') return <FractionsAnimation playing={playing} />;
  if (type === 'plant_parts') return <PlantPartsAnimation playing={playing} />;
  if (type === 'digestion') return <DigestionAnimation playing={playing} />;
  const content = `${scene?.title || ''} ${scene?.caption || ''} ${scene?.visual || ''}`.toLowerCase();
  if (type === 'ionic_bond' || content.includes('ionic') || content.includes('electron') || content.includes('atom') || content.includes('bond')) {
    return <IonicBondAnimation sceneIndex={sceneIndex} playing={playing} />;
  }
  return <GenericConceptAnimation playing={playing} />;
}

function IonicBondAnimation({ sceneIndex, playing }) {
  const showTransfer = sceneIndex >= 1 || playing;
  const showIons = sceneIndex >= 2 || playing;

  return (
    <div className="mb-6">
      <svg viewBox="0 0 640 300" className="w-full max-w-xl mx-auto">
        <defs>
          <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="8" stdDeviation="8" floodOpacity="0.18" />
          </filter>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#2563eb" />
          </marker>
        </defs>

        <rect x="20" y="20" width="600" height="260" rx="28" fill="#ffffffcc" stroke="#dbeafe" />

        <g filter="url(#softShadow)">
          <circle cx="170" cy="145" r="62" fill="#dbeafe" stroke="#60a5fa" strokeWidth="3" />
          <circle cx="170" cy="145" r="28" fill="#3b82f6" />
          <text x="170" y="153" textAnchor="middle" fontSize="24" fontWeight="700" fill="white">Na</text>
          <text x="170" y="235" textAnchor="middle" fontSize="18" fontWeight="700" fill="#1d4ed8">Sodium</text>
        </g>

        <g filter="url(#softShadow)">
          <circle cx="470" cy="145" r="62" fill="#dcfce7" stroke="#4ade80" strokeWidth="3" />
          <circle cx="470" cy="145" r="28" fill="#22c55e" />
          <text x="470" y="153" textAnchor="middle" fontSize="24" fontWeight="700" fill="white">Cl</text>
          <text x="470" y="235" textAnchor="middle" fontSize="18" fontWeight="700" fill="#15803d">Chlorine</text>
        </g>

        <circle cx="215" cy="102" r="9" fill="#f59e0b" className={playing ? 'animate-pulse' : ''} />
        <text x="215" y="82" textAnchor="middle" fontSize="13" fill="#92400e">electron</text>

        {showTransfer && (
          <>
            <path d="M235 102 C300 60, 385 60, 440 102" fill="none" stroke="#2563eb" strokeWidth="4" strokeDasharray="8 8" markerEnd="url(#arrow)" className={playing ? 'animate-pulse' : ''} />
            <circle cx={playing ? 420 : 320} cy={playing ? 105 : 70} r="11" fill="#f59e0b" className="transition-all duration-1000" />
            <text x="320" y="45" textAnchor="middle" fontSize="15" fontWeight="700" fill="#1e40af">electron transfer</text>
          </>
        )}

        {showIons && (
          <>
            <text x="170" y="58" textAnchor="middle" fontSize="26" fontWeight="800" fill="#2563eb">Na⁺</text>
            <text x="470" y="58" textAnchor="middle" fontSize="26" fontWeight="800" fill="#16a34a">Cl⁻</text>
            <path d="M245 175 C315 220, 390 220, 440 175" fill="none" stroke="#ef4444" strokeWidth="4" markerEnd="url(#arrow)" />
            <text x="320" y="255" textAnchor="middle" fontSize="16" fontWeight="700" fill="#991b1b">opposite charges attract</text>
          </>
        )}
      </svg>
    </div>
  );
}

function GenericConceptAnimation({ playing }) {
  return (
    <div className="mb-6">
      <svg viewBox="0 0 640 300" className="w-full max-w-xl mx-auto">
        <rect x="20" y="20" width="600" height="260" rx="28" fill="#ffffffcc" stroke="#dbeafe" />
        <circle cx="180" cy="150" r="54" fill="#dbeafe" stroke="#60a5fa" strokeWidth="3" className={playing ? 'animate-pulse' : ''} />
        <rect x="270" y="96" width="120" height="108" rx="22" fill="#dcfce7" stroke="#4ade80" strokeWidth="3" className={playing ? 'animate-pulse' : ''} />
        <circle cx="500" cy="150" r="54" fill="#fef3c7" stroke="#facc15" strokeWidth="3" className={playing ? 'animate-pulse' : ''} />
        <path d="M230 150 L270 150" stroke="#2563eb" strokeWidth="5" markerEnd="url(#genericArrow)" />
        <path d="M390 150 L445 150" stroke="#2563eb" strokeWidth="5" markerEnd="url(#genericArrow)" />
        <defs>
          <marker id="genericArrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#2563eb" />
          </marker>
        </defs>
        <text x="180" y="155" textAnchor="middle" fontSize="18" fontWeight="700" fill="#1d4ed8">Idea</text>
        <text x="330" y="155" textAnchor="middle" fontSize="18" fontWeight="700" fill="#15803d">Example</text>
        <text x="500" y="155" textAnchor="middle" fontSize="18" fontWeight="700" fill="#a16207">Practice</text>
        <text x="320" y="255" textAnchor="middle" fontSize="16" fontWeight="700" fill="#334155">step-by-step learning</text>
      </svg>
    </div>
  );
}

function PhotosynthesisAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="Photosynthesis" labels={['Sunlight', 'Leaf', 'Food + Oxygen']} colors={['#fde68a', '#bbf7d0', '#bfdbfe']} footer="plants use sunlight to make food" />;
}

function FoodChainAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="Food Chain" labels={['Plant', 'Deer', 'Tiger']} colors={['#bbf7d0', '#fed7aa', '#fecaca']} footer="energy moves from one living thing to another" />;
}

function WaterCycleAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="Water Cycle" labels={['Evaporation', 'Clouds', 'Rain']} colors={['#bae6fd', '#e0e7ff', '#bfdbfe']} footer="water moves through air, clouds, and rain" />;
}

function StatesOfMatterAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="States of Matter" labels={['Solid', 'Liquid', 'Gas']} colors={['#ddd6fe', '#bae6fd', '#fef3c7']} footer="matter changes form when heat changes" />;
}

function ElectricCircuitAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="Electric Circuit" labels={['Battery', 'Wire', 'Bulb']} colors={['#fecaca', '#e5e7eb', '#fde68a']} footer="electricity flows in a closed path" />;
}

function FractionsAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="Fractions" labels={['Whole', 'Parts', 'Fraction']} colors={['#bfdbfe', '#d9f99d', '#fed7aa']} footer="a fraction shows part of a whole" />;
}

function PlantPartsAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="Plant Parts" labels={['Roots', 'Stem', 'Leaves']} colors={['#92400e33', '#bbf7d0', '#86efac']} footer="each plant part has a job" />;
}

function DigestionAnimation({ playing }) {
  return <SimpleDiagram playing={playing} title="Digestion" labels={['Mouth', 'Stomach', 'Energy']} colors={['#fecaca', '#fed7aa', '#bbf7d0']} footer="food breaks down to give energy" />;
}

function SimpleDiagram({ playing, title, labels, colors, footer }) {
  return (
    <div className="mb-6">
      <svg viewBox="0 0 640 300" className="w-full max-w-xl mx-auto">
        <defs>
          <marker id={`arrow-${title}`} markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#2563eb" />
          </marker>
        </defs>
        <rect x="20" y="20" width="600" height="260" rx="28" fill="#ffffffcc" stroke="#dbeafe" />
        <text x="320" y="58" textAnchor="middle" fontSize="22" fontWeight="800" fill="#1e3a8a">{title}</text>
        {labels.map((label, index) => {
          const x = 160 + index * 160;
          return (
            <g key={label}>
              <circle cx={x} cy="145" r={index === 1 ? 58 : 50} fill={colors[index]} stroke="#60a5fa" strokeWidth="3" className={playing ? 'animate-pulse' : ''} />
              <text x={x} y="151" textAnchor="middle" fontSize="17" fontWeight="700" fill="#1f2937">{label}</text>
              {index < labels.length - 1 && <path d={`M${x + 55} 145 L${x + 105} 145`} stroke="#2563eb" strokeWidth="5" markerEnd={`url(#arrow-${title})`} />}
            </g>
          );
        })}
        <text x="320" y="250" textAnchor="middle" fontSize="16" fontWeight="700" fill="#334155">{footer}</text>
      </svg>
    </div>
  );
}

function inferAnimationType(lesson) {
  const lower = `${lesson?.subject || ''} ${lesson?.chapter || ''} ${lesson?.content_text || ''}`.toLowerCase();
  if (lower.includes('ionic') || lower.includes('bond') || lower.includes('electron')) return 'ionic_bond';
  if (lower.includes('photosynthesis')) return 'photosynthesis';
  if (lower.includes('food chain') || lower.includes('ecosystem')) return 'food_chain';
  if (lower.includes('water cycle') || lower.includes('evaporation')) return 'water_cycle';
  if (lower.includes('solid') || lower.includes('liquid') || lower.includes('gas') || lower.includes('states of matter')) return 'states_of_matter';
  if (lower.includes('circuit') || lower.includes('electric')) return 'electric_circuit';
  if (lower.includes('fraction')) return 'fractions';
  if (lower.includes('plant') || lower.includes('root') || lower.includes('stem') || lower.includes('leaf')) return 'plant_parts';
  if (lower.includes('digestion') || lower.includes('digestive')) return 'digestion';
  return 'default_concept';
}

function getReadableText(activeTab, lesson, scenes) {
  if (activeTab === 'animation') return scenes.map((scene) => scene.narration || scene.caption).join('. ');
  if (activeTab === 'keypoints') return lesson.key_points?.join('. ') || '';
  if (activeTab === 'vocab') return lesson.vocabulary?.map((item) => `${item.word}. ${item.definition}`).join('. ') || '';
  if (activeTab === 'captions') return lesson.caption_text || scenes.map((scene) => scene.caption).join('. ');
  if (activeTab === 'visual') return lesson.visual_description || '';
  return lesson.content_text || '';
}

function adaptTextForLevel(text, level) {
  if (!text) return '';
  if (level === 'basic') {
    return text
      .split(/(?<=[.!?])\s+/)
      .slice(0, 6)
      .join(' ');
  }
  if (level === 'advanced') return text;
  return text;
}


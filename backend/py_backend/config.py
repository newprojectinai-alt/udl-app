from pathlib import Path
from dotenv import load_dotenv
import os


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

PORT = int(os.getenv("PORT", "5000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
FRONTEND_URLS = [
    url.strip().rstrip("/")
    for url in os.getenv("FRONTEND_URLS", FRONTEND_URL).split(",")
    if url.strip()
]
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")
APP_URL = os.getenv("APP_URL", "http://localhost:5173")

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_VIDEO_MODEL = os.getenv("HF_VIDEO_MODEL", "zai-org/CogVideoX-5b")
HF_VIDEO_ENDPOINT = os.getenv("HF_VIDEO_ENDPOINT", "").strip()
VIDEO_API_ENDPOINT = os.getenv("VIDEO_API_ENDPOINT", "").strip()
VIDEO_API_TOKEN = os.getenv("VIDEO_API_TOKEN", "")
VIDEO_API_MODE = os.getenv("VIDEO_API_MODE", "sync").strip().lower()
VIDEO_API_POLL_SECONDS = max(1, int(os.getenv("VIDEO_API_POLL_SECONDS", "5")))
VIDEO_API_REQUEST_TIMEOUT_SECONDS = max(10, int(os.getenv("VIDEO_API_REQUEST_TIMEOUT_SECONDS", "90")))
HF_VIDEO_TIMEOUT_SECONDS = int(os.getenv("HF_VIDEO_TIMEOUT_SECONDS", "900"))
HF_VIDEO_NUM_FRAMES = int(os.getenv("HF_VIDEO_NUM_FRAMES", "49"))
HF_VIDEO_GUIDANCE_SCALE = float(os.getenv("HF_VIDEO_GUIDANCE_SCALE", "6.0"))

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "")).strip()
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "").strip()
AWS_S3_PREFIX = os.getenv("AWS_S3_PREFIX", "udl-learn").strip().strip("/")
AWS_S3_PRESIGNED_TTL_SECONDS = max(60, int(os.getenv("AWS_S3_PRESIGNED_TTL_SECONDS", "3600")))

PYTHON_COMMAND = os.getenv("PYTHON_COMMAND", "python")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")
SKIP_TTS = os.getenv("SKIP_TTS", "false").lower() == "true"

VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "854"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "480"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "20"))
VIDEO_DURATION_SECONDS = int(os.getenv("VIDEO_DURATION_SECONDS", "30"))
CARTOON_FRAME_FPS = int(os.getenv("CARTOON_FRAME_FPS", "8"))
MANIM_QUALITY = os.getenv("MANIM_QUALITY", "l")
MANIM_RENDER_TIMEOUT_SECONDS = int(os.getenv("MANIM_RENDER_TIMEOUT_SECONDS", "240"))

UPLOADS_DIR = BACKEND_ROOT / "uploads"
RENDERS_DIR = BACKEND_ROOT / "renders"
AUDIO_DIR = BACKEND_ROOT / "audio"
VIDEO_FRAMES_DIR = BACKEND_ROOT / "video_frames"
MANIM_JOBS_DIR = BACKEND_ROOT / "manim_jobs"

for directory in (UPLOADS_DIR, RENDERS_DIR, AUDIO_DIR, VIDEO_FRAMES_DIR, MANIM_JOBS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

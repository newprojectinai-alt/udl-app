# UDL Learn Python Backend

This folder now contains only the Python/FastAPI backend for the UDL Learn app.


## Main Files

- `app.py` — FastAPI API routes
- `py_backend/` — Python services for AI, Supabase, RAG, TTS, and video rendering
- `requirements.txt` — Python dependencies
- `start-python.ps1` — Windows launcher
- `db/schema.sql` — Supabase database schema
- `tts/kokoro_tts.py` — local Kokoro narration helper
- `uploads/`, `audio/`, `renders/`, `video_frames/` — generated files

## Run Backend

From this folder:

```powershell
.\start-python.ps1
```

Manual version:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --reload --host 0.0.0.0 --port 5000
```

Health check:

```txt
http://localhost:5000/api/health
```

## Environment

Create/edit:

```txt
backend/.env
```

Required for Supabase mode:

```env
PORT=5000
FRONTEND_URL=http://localhost:5173

SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
SUPABASE_STORAGE_BUCKET=textbooks
```

AI provider options:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

or:

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemma-3-27b-it:free
APP_URL=http://localhost:5173
```

Video/TTS settings:

```env
PYTHON_COMMAND=python
KOKORO_VOICE=af_heart
VIDEO_WIDTH=854
VIDEO_HEIGHT=480
VIDEO_FPS=20
VIDEO_DURATION_SECONDS=30
CARTOON_FRAME_FPS=8
MANIM_QUALITY=l
MANIM_RENDER_TIMEOUT_SECONDS=240
SKIP_TTS=false
```

Hugging Face video settings:

```env
VIDEO_API_ENDPOINT=http://YOUR_GPU_SERVER_IP:8000/generate
VIDEO_API_TOKEN=choose-a-long-random-secret
HF_TOKEN=your_hugging_face_token_here
HF_VIDEO_MODEL=zai-org/CogVideoX-5b
HF_VIDEO_ENDPOINT=
HF_VIDEO_TIMEOUT_SECONDS=900
HF_VIDEO_NUM_FRAMES=49
HF_VIDEO_GUIDANCE_SCALE=6.0
```

Preferred setup: run `../cogvideo-server` on your rented RTX 4090 machine and set `VIDEO_API_ENDPOINT` to that server's `/generate` URL. Keep tokens only in `backend/.env`, never in frontend files.

## Manim Troubleshooting

If rendering fails with a long Manim/NumPy traceback ending in `KeyboardInterrupt`, the dev server was probably restarted while Manim was importing or rendering. Run the backend with:

```powershell
.\start-python.ps1
```

The launcher excludes generated folders such as `manim_jobs/`, `renders/`, `audio/`, `uploads/`, and `video_frames/` from FastAPI auto-reload.

## API Areas

- `GET /api/health`
- `/api/textbooks`
- `/api/lessons`
- `/api/assessments`
- `/api/users`
- `/api/reports`
- `/api/rag`
- `/api/videos`

## Current AI Workflow

```txt
Admin uploads PDF/image/text
↓
Python extracts text/OCR
↓
Text chunks saved for RAG
↓
Student generates lesson
↓
AI creates UDL lesson + storyboard
↓
Student chooses video character
↓
Kokoro creates narration
↓
Pillow draws cartoon frames
↓
MoviePy exports MP4
```

## Production Notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` only on the backend.
- Do not put AI keys or service role keys in React/frontend files.
- For heavier AI/video generation, replace FastAPI `BackgroundTasks` with a real worker queue such as Celery or RQ.

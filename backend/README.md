# UDL Learn Python Backend

FastAPI backend for the UDL Learn app.

## Main Files

- `app.py` - FastAPI API routes
- `py_backend/` - Python services for AI, Supabase, RAG, TTS, S3, and CogVideoX orchestration
- `requirements.txt` - Python dependencies
- `start-python.ps1` - Windows launcher
- `db/schema.sql` - Supabase database schema
- `tts/kokoro_tts.py` - local Kokoro narration helper
- `uploads/`, `audio/`, `renders/` - temporary generated files before S3 upload

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

Create/edit `backend/.env`.

Required for Supabase mode:

```env
PORT=5000
FRONTEND_URL=http://localhost:5173
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
```

AI provider example:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

CogVideoX/RunPod video settings:

```env
VIDEO_API_ENDPOINT=https://YOUR_POD_ID-8000.proxy.runpod.net/jobs
VIDEO_API_TOKEN=choose-a-long-random-secret
VIDEO_API_MODE=async
VIDEO_API_POLL_SECONDS=5
VIDEO_API_REQUEST_TIMEOUT_SECONDS=90
HF_VIDEO_TIMEOUT_SECONDS=900
HF_VIDEO_NUM_FRAMES=49
HF_VIDEO_NUM_STEPS=30
HF_VIDEO_GUIDANCE_SCALE=6.0
HF_VIDEO_MIN_BYTES=100000
```

AWS S3 media storage:

```env
AWS_REGION=eu-central-1
AWS_S3_BUCKET=your-private-media-bucket
AWS_S3_PREFIX=udl-learn
AWS_S3_PRESIGNED_TTL_SECONDS=3600
```

TTS settings:

```env
PYTHON_COMMAND=python
KOKORO_VOICE=af_heart
SKIP_TTS=false
```

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
-> Python extracts text/OCR
-> Text chunks saved for RAG
-> Student generates lesson
-> AI creates UDL lesson + storyboard
-> Kokoro creates narration
-> Backend sends CogVideoX prompt to RunPod
-> Backend validates/transcodes MP4
-> Backend uploads MP4 to private S3
```

## Production Notes

- Keep `SUPABASE_SERVICE_ROLE_KEY`, AI keys, and `VIDEO_API_TOKEN` only on the backend.
- Do not put secrets in React/frontend files.
- FastAPI `BackgroundTasks` are acceptable for an MVP; use a queue/worker for production reliability.

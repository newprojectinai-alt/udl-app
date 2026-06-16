# UDL Learn Standalone App

This is the standalone React/Vite version of the Base44 UDL learning app. Base44 dependencies have been removed.

## Important: Open The Correct Folder

In VS Code, open this folder directly:

```txt
C:\Users\rojin\OneDrive\Documents\New project\udl-standalone-app
```

If you are using the newer folder from our changes, open:

```txt
C:\Users\rojin\OneDrive\Documents\New project\udl-standalone-app-source2
```

Do **not** open only:

```txt
C:\Users\rojin\OneDrive\Documents\New project
```

That parent folder contains your older `Lecture2Quiz` app, so if you run commands there you will see the Lecture2Quiz interface.

## How To Run

Open a terminal inside `udl-standalone-app`, then run:

```bash
npm install
npm run dev
```

Then open the localhost URL shown by Vite, usually:

```txt
http://localhost:5173
```

## What You Should See

The first page should say:

```txt
UDL Learn
```

It has three buttons:

- Enter as Student
- Enter as Teacher
- Enter as Admin

## Current Database

This version uses browser `localStorage`, so it can run without a backend.

Important files:

- `src/data/localSeedData.js` — demo textbooks, users, students, teachers
- `src/services/localStore.js` — saves and loads localStorage data
- `src/services/entityService.js` — replaces Base44 entity methods

This is good for testing the UI locally, but it is not the final production database.

## Real Backend Mode

I added a production-ready backend starter in:

```txt
backend
```

To use the real backend instead of localStorage:

1. Create frontend `.env` from `.env.example`.
2. Set:

```env
VITE_API_BASE_URL=http://localhost:5000
VITE_USE_BACKEND=true
```

3. Set up backend `.env` in `backend/.env`.
4. Run the Supabase SQL schema in `backend/db/schema.sql`.
5. Start backend and frontend separately.

Frontend:

```bash
npm run dev
```

Python backend:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 5000
```

The older Node/Express backend files have been removed. The backend is now the Python FastAPI app in `backend/app.py`.

## Recommended Production Database

Use PostgreSQL.

Recommended options:

- Supabase PostgreSQL — easiest hosted option
- Neon PostgreSQL — good serverless option
- Local PostgreSQL — good for development

Suggested tables:

- `users`
- `student_profiles`
- `teacher_profiles`
- `textbooks`
- `lesson_contents`
- `assessments`
- `assessment_results`

## Where API Keys Should Go

Do **not** put API keys inside React files.

For production, add secrets only in `backend/.env`:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
```

Then React should call backend endpoints like:

- `POST /api/lessons/generate`
- `POST /api/assessments/generate`
- `POST /api/assessments/:id/complete`
- `POST /api/textbooks/upload`

## Free AI API Recommendation

Use Gemini from Google AI Studio first.

Get a key here:

```txt
https://aistudio.google.com/app/apikey
```

Put it only in:

```txt
backend/.env
```

Do not put it in React/frontend `.env`.

If Gemini is busy, use OpenRouter as a free backup:

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemma-3-27b-it:free
```

Put these only in `backend/.env`.

## Current AI Logic

For now, mock AI is here:

```txt
src/services/aiService.js
```

It currently creates sample:

- chapters
- lessons
- quizzes
- flashcards
- feedback

Later, replace this mock logic with calls to your backend API.

## Current Authentication

This version uses local role switching.

On the landing page you can enter as:

- Student
- Teacher
- Admin

Production should later use:

- Supabase Auth
- Firebase Auth
- Clerk
- or custom JWT login

## Main Technologies

- React
- Vite
- Tailwind CSS
- React Router
- TanStack Query
- Recharts
- LocalStorage data service

## Admin Text Input And OCR

The Admin textbook upload page now supports:

- PDF upload
- image upload with OCR
- pasted textbook/chapter text

The pasted text option is fastest and most reliable. The AI uses saved textbook text later when a student starts a lesson, then adapts the lesson to the student's profile level:

- Basic
- Standard
- Advanced

from pathlib import Path
import random
import time
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from py_backend import config
from py_backend.ai import (
    answer_from_context,
    extract_chapters,
    generate_assessment,
    generate_feedback,
    generate_lesson,
)
from py_backend.database import (
    SupabaseError,
    create_record,
    delete_record,
    filter_records,
    get_record,
    list_records,
    update_record,
)
from py_backend.rag import create_textbook_chunks, retrieve_relevant_chunks
from py_backend.text_processing import extract_text_from_image, extract_text_from_pdf, infer_chapters_locally
from py_backend.video import create_video_job_for_lesson, get_latest_video_job_for_lesson, render_video_job


app = FastAPI(title="UDL Learn Python API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(config.UPLOADS_DIR)), name="uploads")
app.mount("/renders", StaticFiles(directory=str(config.RENDERS_DIR)), name="renders")
app.mount("/audio", StaticFiles(directory=str(config.AUDIO_DIR)), name="audio")


@app.exception_handler(SupabaseError)
async def supabase_exception_handler(_request: Request, exc: SupabaseError):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc)})


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, exc: Exception):
    print(exc)
    return JSONResponse(status_code=500, content={"error": str(exc) or "Internal server error"})


@app.get("/api/health")
def health():
    return {"ok": True, "name": "UDL Learn Python API"}


@app.get("/api/textbooks")
def list_textbooks(class_level: str | None = None, subject: str | None = None, status: str | None = None):
    filters = {"class_level": class_level, "subject": subject, "status": status}
    return filter_records("textbooks", filters) if any(filters.values()) else list_records("textbooks")


@app.post("/api/textbooks")
async def create_textbook(request: Request):
    return create_record("textbooks", await request.json())


@app.post("/api/textbooks/upload", status_code=201)
async def upload_textbook(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    class_level: str = Form(...),
    subject: str = Form(...),
    uploaded_by: str | None = Form(None),
    text_content: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    if not file and not (text_content or "").strip():
        raise HTTPException(status_code=400, detail="Upload a PDF/image or paste textbook text")

    file_url = ""
    storage_path = ""
    file_path = None
    mime_type = ""

    if file:
        suffix = Path(file.filename or "").suffix
        safe_name = f"{uuid4().hex}{suffix}"
        file_path = config.UPLOADS_DIR / safe_name
        file_path.write_bytes(await file.read())
        file_url = f"/uploads/{safe_name}"
        storage_path = str(file_path)
        mime_type = file.content_type or ""

    record = create_record("textbooks", {
        "title": title,
        "class_level": class_level,
        "subject": subject,
        "uploaded_by": uploaded_by,
        "file_url": file_url,
        "storage_path": storage_path,
        "status": "processing",
        "extracted_text": (text_content or "").strip(),
    })

    background_tasks.add_task(
        process_textbook_in_background,
        record["id"],
        str(file_path) if file_path else None,
        mime_type,
        (text_content or "").strip(),
        title,
        class_level,
        subject,
    )
    return record


def process_textbook_in_background(record_id, file_path, mime_type, pasted_text, title, class_level, subject):
    try:
        print("Processing textbook chapters:", {"recordId": record_id, "title": title})
        extracted_text = pasted_text or ""
        chapter_result = None

        if not extracted_text and file_path:
            try:
                extracted_text = extract_text_from_image(file_path) if mime_type.startswith("image/") else extract_text_from_pdf(file_path)
            except Exception as exc:
                print(f"Text extraction failed; using fallback chapters: {exc}")

        if extracted_text:
            chapter_result = extract_chapters(title, subject, class_level, extracted_text)

        chapters = chapter_result.get("chapters") if chapter_result else None
        chapters = chapters if chapters else infer_chapters_locally(extracted_text, title)

        update_record("textbooks", record_id, {
            "extracted_text": extracted_text,
            "chapters": chapters,
            "status": "ready",
        })

        if extracted_text:
            chunks = create_textbook_chunks(record_id, class_level, subject, chapters, extracted_text)
            print("Textbook chunks indexed:", {"recordId": record_id, "chunks": len(chunks)})
    except Exception as exc:
        print(f"Background textbook processing failed: {exc}")
        update_record("textbooks", record_id, {
            "status": "ready",
            "extracted_text": pasted_text or "",
            "chapters": infer_chapters_locally(pasted_text, title),
        })


@app.patch("/api/textbooks/{record_id}")
async def patch_textbook(record_id: str, request: Request):
    return update_record("textbooks", record_id, await request.json())


@app.delete("/api/textbooks/{record_id}")
def remove_textbook(record_id: str):
    return delete_record("textbooks", record_id)


@app.get("/api/lessons")
def list_lessons(request: Request):
    return filter_records("lessons", dict(request.query_params))


@app.post("/api/lessons/generate", status_code=201)
async def create_lesson(request: Request):
    body = await request.json()
    class_level = body.get("class_level")
    subject = body.get("subject")
    chapter = body.get("chapter")
    iq_level = body.get("iq_level")
    textbook_id = body.get("textbook_id")

    existing = filter_records("lessons", {
        "class_level": class_level,
        "subject": subject,
        "chapter": chapter,
        "iq_level": iq_level,
    })
    if existing:
        return existing[0]

    textbook_context = body.get("textbook_text") or ""
    if not textbook_context:
        try:
            chunks = retrieve_relevant_chunks(
                textbook_id=textbook_id,
                class_level=class_level,
                subject=subject,
                chapter=chapter,
                query=chapter,
                limit=6,
            )
            textbook_context = "\n\n---\n\n".join(chunk.get("content", "") for chunk in chunks)
        except Exception as exc:
            print(f"Could not load RAG context for lesson generation: {exc}")

    if not textbook_context and textbook_id:
        try:
            textbook = get_record("textbooks", textbook_id)
            textbook_context = (textbook.get("extracted_text") or "")[:8000]
        except Exception as exc:
            print(f"Could not load textbook fallback context: {exc}")

    content = generate_lesson(
        class_level=class_level,
        subject=subject,
        chapter=chapter,
        iq_level=iq_level,
        disabilities=body.get("disabilities") or [],
        textbook_text=textbook_context,
    )
    content["animation_type"] = normalize_animation_type(content.get("animation_type"), f"{subject} {chapter} {content.get('content_text') or ''}")
    return create_record("lessons", {
        "textbook_id": textbook_id,
        "class_level": class_level,
        "subject": subject,
        "chapter": chapter,
        "iq_level": iq_level,
        **content,
    })


@app.get("/api/lessons/{record_id}")
def get_lesson(record_id: str):
    return get_record("lessons", record_id)


@app.get("/api/assessments")
def list_assessments(request: Request):
    return filter_records("assessments", dict(request.query_params))


@app.get("/api/assessments/{record_id}")
def get_assessment(record_id: str):
    return get_record("assessments", record_id)


@app.post("/api/assessments/generate", status_code=201)
async def create_assessment(request: Request):
    body = await request.json()
    result = generate_assessment(
        class_level=body.get("class_level"),
        subject=body.get("subject"),
        chapter=body.get("chapter"),
        assessment_type=body.get("assessment_type"),
        iq_level=body.get("iq_level"),
        generation_seed=f"{int(time.time())}-{random.randint(1000, 9999)}",
    )
    questions = result.get("questions") or build_local_assessment_questions(
        body.get("chapter"),
        body.get("assessment_type"),
        body.get("iq_level"),
    )
    return create_record("assessments", {
        "student_email": body.get("student_email"),
        "class_level": body.get("class_level"),
        "subject": body.get("subject"),
        "chapter": body.get("chapter"),
        "assessment_type": body.get("assessment_type"),
        "iq_level": body.get("iq_level"),
        "questions": questions,
        "total_questions": len(questions),
        "completed": False,
    })


@app.patch("/api/assessments/{record_id}")
async def patch_assessment(record_id: str, request: Request):
    return update_record("assessments", record_id, await request.json())


@app.post("/api/assessments/{record_id}/complete")
async def complete_assessment(record_id: str, request: Request):
    assessment = get_record("assessments", record_id)
    body = await request.json()
    answers = body.get("answers") or {}
    questions = assessment.get("questions") or []
    score = sum(1 for index, question in enumerate(questions) if answers.get(str(index), answers.get(index)) == question.get("correct_answer"))
    percentage = round((score / len(questions)) * 100) if questions else 0
    ai_feedback = generate_feedback(assessment, score, percentage)

    updated_questions = []
    for index, question in enumerate(questions):
        answer = answers.get(str(index), answers.get(index, ""))
        updated_questions.append({
            **question,
            "student_answer": answer,
            "is_correct": answer == question.get("correct_answer"),
        })

    return update_record("assessments", record_id, {
        "questions": updated_questions,
        "score": score,
        "time_spent_seconds": body.get("time_spent_seconds"),
        "completed": True,
        "ai_feedback": ai_feedback,
    })


@app.get("/api/users/students")
def students():
    return list_records("students")


@app.get("/api/users/teachers")
def teachers():
    return list_records("teachers")


@app.get("/api/users/students/by-email/{email}")
def students_by_email(email: str):
    return filter_records("students", {"user_email": email})


@app.post("/api/users/students", status_code=201)
async def create_student(request: Request):
    return create_record("students", await request.json())


@app.patch("/api/users/students/{record_id}")
async def patch_student(record_id: str, request: Request):
    return update_record("students", record_id, await request.json())


@app.delete("/api/users/students/{record_id}")
def remove_student(record_id: str):
    return delete_record("students", record_id)


@app.get("/api/reports/platform")
def platform_report():
    students_data = list_records("students")
    teachers_data = list_records("teachers")
    textbooks_data = list_records("textbooks")
    assessments_data = list_records("assessments")
    completed = [assessment for assessment in assessments_data if assessment.get("completed")]
    avg_score = (
        sum((assessment.get("score") or 0) / (assessment.get("total_questions") or 1) * 100 for assessment in completed) / len(completed)
        if completed else 0
    )
    return {
        "students": len(students_data),
        "teachers": len(teachers_data),
        "textbooks": len(textbooks_data),
        "assessments": len(assessments_data),
        "completedAssessments": len(completed),
        "avgScore": avg_score,
    }


@app.post("/api/rag/ask")
async def rag_ask(request: Request):
    body = await request.json()
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    chunks = retrieve_relevant_chunks(
        textbook_id=body.get("textbook_id"),
        class_level=body.get("class_level"),
        subject=body.get("subject"),
        chapter=body.get("chapter"),
        query=question,
        limit=6,
    )
    context = "\n\n---\n\n".join(chunk.get("content", "") for chunk in chunks)
    answer = answer_from_context(question, context, body.get("student_level") or "standard")
    return {
        **answer,
        "sources": [
            {
                "textbook_id": chunk.get("textbook_id"),
                "chunk_index": chunk.get("chunk_index"),
                "chapter": chunk.get("chapter"),
            }
            for chunk in chunks
        ],
    }


@app.post("/api/videos/generate", status_code=201)
async def video_generate(request: Request):
    body = await request.json()
    lesson_id = body.get("lesson_id")
    if not lesson_id:
        raise HTTPException(status_code=400, detail="lesson_id is required")
    return create_video_job_for_lesson(
        lesson_id,
        character=body.get("character") or "maya",
        renderer=body.get("renderer") or "cartoon",
    )


@app.get("/api/videos/lesson/{lesson_id}/latest")
def video_latest(lesson_id: str):
    return get_latest_video_job_for_lesson(lesson_id)


@app.get("/api/videos/{job_id}")
def video_get(job_id: str):
    return get_record("video_jobs", job_id)


@app.post("/api/videos/{job_id}/render")
def video_render(job_id: str, background_tasks: BackgroundTasks):
    job = get_record("video_jobs", job_id)
    if job.get("status") == "rendering":
        return job
    if job.get("video_url"):
        return job

    queued_job = update_record("video_jobs", job_id, {
        "status": "rendering",
        "error_message": None,
        "provider_metadata": {
            **(job.get("provider_metadata") or {}),
            "progress_label": "Queued for rendering",
            "progress_percent": 5,
        },
    })
    background_tasks.add_task(render_video_job, job_id)
    return queued_job


def normalize_animation_type(animation_type, text):
    allowed = {
        "ionic_bond", "photosynthesis", "food_chain", "water_cycle", "states_of_matter",
        "electric_circuit", "fractions", "plant_parts", "digestion", "default_concept",
    }
    if animation_type in allowed:
        return animation_type
    lower = (text or "").lower()
    if "ionic" in lower or "bond" in lower or "electron" in lower:
        return "ionic_bond"
    if "photosynthesis" in lower:
        return "photosynthesis"
    if "food chain" in lower or "ecosystem" in lower:
        return "food_chain"
    if "water cycle" in lower or "evaporation" in lower:
        return "water_cycle"
    if "solid" in lower or "liquid" in lower or "gas" in lower or "states of matter" in lower:
        return "states_of_matter"
    if "circuit" in lower or "electric" in lower:
        return "electric_circuit"
    if "fraction" in lower:
        return "fractions"
    if "plant" in lower or "root" in lower or "stem" in lower or "leaf" in lower:
        return "plant_parts"
    if "digestion" in lower or "digestive" in lower:
        return "digestion"
    return "default_concept"


def build_local_assessment_questions(chapter, assessment_type, iq_level):
    topic = chapter or "this lesson"
    variants = [
        {
            "question": f"Mystery clue: I am the most important idea in {topic}. Which answer fits?",
            "question_type": "clue_match",
            "options": [f"Main idea of {topic}", "A random word", "An unrelated story", "Only the page number"],
            "correct_answer": f"Main idea of {topic}",
            "hint": "Look for the choice connected to the lesson topic.",
        },
        {
            "question": f"Odd one out: Which option does not help you understand {topic}?",
            "question_type": "odd_one_out",
            "options": ["Reading key points", "Looking at examples", "Guessing without reading", "Asking questions"],
            "correct_answer": "Guessing without reading",
            "hint": "Find the choice that is not a learning strategy.",
        },
        {
            "question": f"Sequence puzzle: What should you do first when learning {topic}?",
            "question_type": "sequence",
            "options": ["Read the main idea", "Look at examples", "Try practice", "Review feedback"],
            "correct_answer": "Read the main idea → Look at examples → Try practice → Review feedback",
            "hint": "Build the best learning order.",
        },
        {
            "question": f"Match the clue: Which activity checks your understanding of {topic}?",
            "question_type": "clue_match",
            "options": ["Trying a quiz", "Ignoring feedback", "Deleting notes", "Avoiding practice"],
            "correct_answer": "Trying a quiz",
            "hint": "Choose the activity that tests what you learned.",
        },
        {
            "question": f"Fill the blank: ______ helps your brain remember {topic}.",
            "question_type": "fill_blank",
            "options": ["Practice", "Confusion", "Noise", "A blank page"],
            "correct_answer": "Practice",
            "hint": "Doing something again helps memory.",
        },
    ]
    if assessment_type == "flashcard":
        return [
            {
                "question": f"Flashcard: What is one key idea from {topic}?",
                "options": [f"A key idea from {topic}", "Unrelated fact", "Wrong answer", "Random word"],
                "correct_answer": f"A key idea from {topic}",
            },
            *variants,
        ][:8]
    if assessment_type == "quiz":
        return [
            {
                **item,
                "question": item["question"].replace("Mystery clue:", "Question:").replace("Odd one out:", "Choose carefully:").replace("Sequence puzzle:", "Order check:").replace("Match the clue:", "Understanding check:").replace("Mini riddle:", "Think:")
            }
            for item in variants
        ]
    return variants

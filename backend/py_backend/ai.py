import json
import re
import time
import uuid
import requests

from . import config


GEMINI_FALLBACK_MODELS = list(dict.fromkeys([
    config.GEMINI_MODEL,
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]))


def extract_json(text: str, fallback: dict):
    try:
        return json.loads(text or "")
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text or "")
        if not match:
            return fallback
        try:
            return json.loads(match.group(0))
        except Exception:
            return fallback


def require_provider():
    if config.AI_PROVIDER == "gemini" and not config.GEMINI_API_KEY:
        raise RuntimeError("Gemini is selected but GEMINI_API_KEY is missing in backend/.env.")
    if config.AI_PROVIDER == "openai" and not config.OPENAI_API_KEY:
        raise RuntimeError("OpenAI is selected but OPENAI_API_KEY is missing in backend/.env.")
    if config.AI_PROVIDER == "openrouter" and not config.OPENROUTER_API_KEY:
        raise RuntimeError("OpenRouter is selected but OPENROUTER_API_KEY is missing in backend/.env.")


def generate_json_with_gemini(prompt: str, fallback: dict):
    require_provider()
    last_error = None
    for model in GEMINI_FALLBACK_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": f"You are an inclusive education assistant for UDL learning. Return valid JSON only.\n\n{prompt}"}],
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.5,
            },
        }
        response = requests.post(url, params={"key": config.GEMINI_API_KEY}, json=payload, timeout=90)
        if response.status_code in (404, 429, 500, 502, 503, 504):
            last_error = response.text
            print(f"Gemini issue on {model} ({response.status_code}). Trying fallback model...")
            time.sleep(0.75)
            continue
        if response.status_code >= 400:
            raise RuntimeError(response.text)
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return extract_json(text, fallback)
    print(f"Gemini failed; using local fallback. Last error: {last_error}")
    return fallback


def generate_json_with_openrouter(prompt: str, fallback: dict):
    require_provider()
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": config.APP_URL,
            "X-Title": "UDL Learn",
        },
        json={
            "model": config.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "You are an inclusive education assistant for UDL learning. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.5,
            "response_format": {"type": "json_object"},
        },
        timeout=90,
    )
    if response.status_code >= 400:
        raise RuntimeError(response.text)
    data = response.json()
    return extract_json(data.get("choices", [{}])[0].get("message", {}).get("content", ""), fallback)


def generate_json_with_openai(prompt: str, fallback: dict):
    require_provider()
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an inclusive education assistant for UDL learning. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        return extract_json(response.choices[0].message.content or "", fallback)
    except Exception as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc


def generate_json(prompt: str, fallback: dict):
    if config.AI_PROVIDER == "openai":
        return generate_json_with_openai(prompt, fallback)
    if config.AI_PROVIDER == "openrouter":
        return generate_json_with_openrouter(prompt, fallback)
    return generate_json_with_gemini(prompt, fallback)


def extract_chapters(title, subject, class_level, extracted_text):
    return generate_json(
        f'Extract chapter/topic names from this Class {class_level} {subject} textbook titled "{title}". '
        f'Return JSON: {{"chapters":["..."]}}. Text sample:\n{(extracted_text or "")[:12000]}',
        {"chapters": ["Introduction", "Core Concepts", "Practice"]},
    )


def generate_lesson(class_level, subject, chapter, iq_level, disabilities=None, textbook_text=""):
    disabilities = disabilities or []
    fallback = {
        "content_text": f"Lesson for {chapter}.",
        "key_points": [],
        "visual_description": "",
        "caption_text": "",
        "vocabulary": [],
        "animation_type": "default_concept",
        "animation_script": [],
    }
    return generate_json(
        f"""Create a UDL lesson for Class {class_level}, Subject {subject}, Chapter "{chapter}".
Cognitive level: {iq_level}.
Disabilities/accommodations: {", ".join(disabilities) if disabilities else "none"}.
Use this textbook context if helpful:
{(textbook_text or "")[:12000]}

Return JSON:
{{
  "content_text": "400-700 word lesson",
  "key_points": ["5 key points"],
  "visual_description": "description for visually impaired students",
  "caption_text": "caption/narration text for hearing impaired students",
  "vocabulary": [{{"word":"", "definition":""}}],
  "animation_type": "one of: ionic_bond, photosynthesis, food_chain, water_cycle, states_of_matter, electric_circuit, fractions, plant_parts, digestion, default_concept",
  "animation_script": [
    {{
      "title": "short scene title",
      "caption": "1-2 sentence caption shown on screen",
      "visual": "simple visual description for animation",
      "narration": "voice narration for this scene"
    }}
  ]
}}""",
        fallback,
    )


def generate_assessment(class_level, subject, chapter, assessment_type, iq_level, generation_seed=None):
    count = 8 if assessment_type == "flashcard" else 5
    seed = generation_seed or uuid.uuid4().hex[:10]
    assessment_guidance = {
        "quiz": "Create varied multiple-choice questions: definitions, application, examples, identify-the-correct-step, and reasoning.",
        "puzzle": "Create playful puzzle-style multiple-choice questions: match-the-clue, sequence/order, odd-one-out, mystery clue, mini riddle, or fill-the-missing-step. Still return four options for each.",
        "flashcard": "Create flashcards with different front-side prompts and concise answers. Include four options for practice mode.",
    }.get(assessment_type, "Create varied multiple-choice questions.")
    return generate_json(
        f"""Generate {count} {assessment_type} questions for Class {class_level}, Subject {subject}, Chapter "{chapter}", Level {iq_level}.
Generation seed: {seed}

{assessment_guidance}

Return JSON:
{{
  "questions": [
    {{
      "question": "",
      "question_type": "mcq | sequence | fill_blank | odd_one_out | clue_match",
      "options": ["", "", "", ""],
      "correct_answer": "",
      "hint": "short helpful hint"
    }}
  ]
}}
Rules:
- Make this set different from previous generations.
- Do not repeat the same question pattern.
- Keep language suitable for Class {class_level}.
- Exactly one option must match correct_answer.
- For flashcards, put the front side in question and answer in correct_answer; still include 4 options.
- For puzzles, start question text with a puzzle label such as "Mystery clue:", "Odd one out:", "Sequence puzzle:", or "Match the clue:".""",
        {"questions": []},
    )


def generate_feedback(assessment, score, percentage):
    result = generate_json(
        f"""A student completed {assessment.get("assessment_type")} for {assessment.get("subject")}, Chapter "{assessment.get("chapter")}", Class {assessment.get("class_level")}.
Score: {score}/{assessment.get("total_questions")} ({percentage}%).
Level: {assessment.get("iq_level")}.
Return JSON: {{"feedback":"2-3 encouraging, specific sentences with what to review."}}""",
        {"feedback": "Good effort. Review the missed questions and try again."},
    )
    return result.get("feedback", "Good effort. Review the missed questions and try again.")


def answer_from_context(question, context, student_level="standard"):
    return generate_json(
        f"""Answer the student's question using only the provided textbook context.
Student level: {student_level}.
If the answer is not in the context, say that the textbook context does not contain enough information.

Question:
{question}

Textbook context:
{context}

Return JSON:
{{
  "answer": "clear answer adapted to the student level",
  "key_points": ["2-4 short points"],
  "follow_up_question": "one simple question to check understanding"
}}""",
        {
            "answer": "The textbook context does not contain enough information to answer this question.",
            "key_points": [],
            "follow_up_question": "",
        },
    )


def generate_video_storyboard(lesson: dict):
    lesson_title = " - ".join(filter(None, [lesson.get("subject"), lesson.get("chapter")])) or lesson.get("chapter") or "Lesson"
    key_points = lesson.get("key_points") or []
    vocabulary = lesson.get("vocabulary") or []
    fallback = {
        "scenes": [
            {
                "title": lesson.get("chapter") or "Lesson Introduction",
                "narration": f"Today we are learning {lesson_title}.",
                "caption": f"Today we are learning {lesson_title}.",
                "visual_layout": "Show a clean title slide with three connected concept cards.",
                "on_screen_text": [lesson.get("chapter") or "Lesson", lesson.get("subject") or "Subject", "Key ideas"],
                "image_prompt": f"simple educational classroom slide about {lesson_title}, clear diagram style",
            }
        ]
    }

    result = generate_json(
        f"""Create a clear educational video storyboard for a UDL lesson.

Lesson title: {lesson_title}
Class level: {lesson.get("class_level")}
Student level: {lesson.get("iq_level")}

Lesson text:
{(lesson.get("content_text") or "")[:9000]}

Key points:
{json.dumps(key_points, ensure_ascii=False)}

Vocabulary:
{json.dumps(vocabulary, ensure_ascii=False)}

Return JSON only:
{{
  "scenes": [
    {{
      "title": "short slide title",
      "narration": "1-2 clear spoken sentences for this scene",
      "caption": "short caption shown on the video",
      "visual_layout": "specific slide layout/diagram to draw, based only on this lesson",
      "on_screen_text": ["3 to 5 short phrases that should appear on the slide"],
      "image_prompt": "prompt for a future educational image generator"
    }}
  ]
}}

Rules:
- Create 5 to 7 scenes.
- Every scene must match the actual lesson topic.
- Avoid generic words like Idea, Example, Practice unless the lesson itself uses them.
- Use simple visual language suitable for deaf and cognitive learners.
- Do not invent unrelated concepts.""",
        fallback,
    )

    scenes = result.get("scenes") if isinstance(result, dict) else None
    if not isinstance(scenes, list) or not scenes:
        return fallback
    return {"scenes": scenes[:7]}

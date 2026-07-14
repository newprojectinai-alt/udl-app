import math
import re
from pathlib import Path

from . import config
from .ai import generate_video_storyboard
from .database import create_record, filter_records, get_record, update_record
from .storage import upload_media, uses_s3
from .text_processing import split_sentences
from .tts import generate_narration_audio


def create_video_job_for_lesson(lesson_id: str, character: str = "maya", renderer: str = "cogvideo"):
    lesson = get_record("lessons", lesson_id)
    scenes = build_storyboard_scenes(lesson)
    narration_text = "\n".join(scene.get("narration") or scene.get("caption") or "" for scene in scenes)
    captions = create_caption_timeline(scenes)
    return create_record("video_jobs", {
        "lesson_id": lesson_id,
        "status": "storyboard_ready",
        "script": lesson.get("content_text") or "",
        "scenes": scenes,
        "narration_text": narration_text,
        "captions": captions,
        "provider_metadata": {
            "workflow": build_workflow(),
            "renderer": "cogvideo_text_to_video",
            "progress_label": "Storyboard ready",
            "progress_percent": 10,
        },
    })


def get_latest_video_job_for_lesson(lesson_id: str):
    jobs = filter_records("video_jobs", {"lesson_id": lesson_id}, limit=1)
    return jobs[0] if jobs else None


def render_video_job(job_id: str):
    job = get_record("video_jobs", job_id)
    update_record("video_jobs", job_id, {"status": "rendering", "error_message": None})
    output_file = config.RENDERS_DIR / f"{job_id}.mp4"
    audio_path = None

    try:
        update_job_progress(job_id, job, "Preparing narration", 15)
        audio = generate_narration_audio(job_id, job.get("narration_text") or job.get("script") or "This lesson is ready.")
        if audio:
            audio_path = audio["audio_path"]
            update_record("video_jobs", job_id, {"audio_url": audio["audio_url"], "audio_status": "ready"})
        else:
            update_record("video_jobs", job_id, {"audio_status": "skipped"})

        job = get_record("video_jobs", job_id)
        update_job_progress(job_id, job, "Generating AI video with CogVideoX", 45)
        from .hf_video import render_huggingface_video
        video_result = render_huggingface_video(
            job_id=job_id,
            job=job,
            output_file=output_file,
            audio_path=audio_path,
        )

        job = get_record("video_jobs", job_id)
        update_job_progress(job_id, job, "Uploading browser-ready MP4", 90)
        video_url = upload_media(output_file, "renders", f"{job_id}.mp4", "video/mp4")
        return update_record("video_jobs", job_id, {
            "status": "completed",
            "video_url": video_url,
            "provider_metadata": {
                **(job.get("provider_metadata") or {}),
                "hf_prompt": video_result.get("prompt"),
                "hf_endpoint": video_result.get("endpoint"),
                "video_output_bytes": video_result.get("output_bytes"),
                "video_output": str(output_file),
                "progress_label": "Video ready",
                "progress_percent": 100,
            },
        })
    except Exception as exc:
        latest_job = get_record("video_jobs", job_id)
        update_record("video_jobs", job_id, {
            "status": "failed",
            "error_message": str(exc),
            "provider_metadata": {
                **(latest_job.get("provider_metadata") or {}),
                "progress_label": "Video failed",
                "progress_percent": latest_job.get("provider_metadata", {}).get("progress_percent", 0),
            },
        })
        raise
    finally:
        if uses_s3():
            output_file.unlink(missing_ok=True)
            (config.AUDIO_DIR / f"{job_id}.wav").unlink(missing_ok=True)


def update_job_progress(job_id: str, job: dict, label: str, percent: int):
    update_record("video_jobs", job_id, {
        "provider_metadata": {
            **(job.get("provider_metadata") or {}),
            "progress_label": label,
            "progress_percent": percent,
        }
    })


def build_workflow():
    return [
        "LLM storyboard",
        "CogVideoX educational prompt",
        "RunPod async GPU generation",
        "MP4 validation",
        "Browser-safe H.264 transcode",
        "Private S3 upload",
    ]


def build_storyboard_scenes(lesson: dict):
    try:
        storyboard = generate_video_storyboard(lesson)
        storyboard_scenes = storyboard.get("scenes") or []
        if storyboard_scenes:
            return normalize_storyboard_scenes(lesson, storyboard_scenes)
    except Exception as exc:
        print(f"LLM storyboard failed; using local scene builder: {exc}")
    return build_scenes_from_lesson(lesson)


def normalize_storyboard_scenes(lesson: dict, storyboard_scenes: list[dict]):
    scenes = []
    for index, scene in enumerate(storyboard_scenes[:6]):
        narration = clean_text(scene.get("narration") or scene.get("caption") or scene.get("title") or "")
        caption = clean_text(scene.get("caption") or narration)
        visual_layout = clean_text(scene.get("visual_layout") or scene.get("image_prompt") or caption or "Educational visual explanation.")
        scenes.append({
            "scene_number": index + 1,
            "title": clean_text(scene.get("title") or f"Scene {index + 1}")[:80],
            "caption": caption[:220],
            "narration": narration[:320],
            "visual_prompt": visual_layout[:420],
            "visual_layout": visual_layout[:420],
            "on_screen_text": sanitize_text_list(scene.get("on_screen_text")),
            "image_prompt": clean_text(scene.get("image_prompt") or visual_layout)[:420],
            "animation_type": detect_animation_type(lesson, scene),
            "duration_seconds": estimate_scene_duration(narration or caption),
            "avatar_clip_url": None,
            "broll_clip_url": None,
        })
    return scenes


def sanitize_text_list(value):
    if not isinstance(value, list):
        return []
    return [clean_text(item)[:36] for item in value if clean_text(item)][:5]


def build_scenes_from_lesson(lesson: dict):
    key_points = [item for item in (lesson.get("key_points") or []) if item]
    content_sentences = split_sentences(lesson.get("content_text") or "")
    main_points = key_points or content_sentences[:5]
    vocabulary = [item for item in (lesson.get("vocabulary") or []) if item.get("word")]
    lesson_title = " - ".join(filter(None, [lesson.get("subject"), lesson.get("chapter")])) or lesson.get("chapter") or "Lesson"

    scenes = [{
        "title": lesson.get("chapter") or "Lesson Introduction",
        "caption": f"Today we are learning {lesson_title}.",
        "visual_layout": f"An educational title scene introducing {lesson_title} with simple topic icons.",
        "narration": f"Today we are learning {lesson_title}.",
    }]

    for index, point in enumerate(main_points[:4]):
        scenes.append({
            "title": create_short_title(point, f"Key Idea {index + 1}"),
            "caption": point,
            "visual_layout": f"Show this idea visually with simple classroom-friendly diagrams: {point}",
            "narration": point,
        })

    if vocabulary:
        words = "; ".join(f"{item.get('word')}: {item.get('definition') or 'important term'}" for item in vocabulary[:3])
        scenes.append({
            "title": "Important Words",
            "caption": words,
            "visual_layout": f"Show clear vocabulary cards for: {words}",
            "narration": words,
        })

    scenes.append({
        "title": "Quick Review",
        "caption": f"Review {lesson.get('chapter') or 'this lesson'} and try the quiz to check your understanding.",
        "visual_layout": "A friendly checklist and quiz card summarizing the lesson.",
        "narration": f"Review {lesson.get('chapter') or 'this lesson'} and try the quiz to check your understanding.",
    })

    return normalize_storyboard_scenes(lesson, scenes)


def create_caption_timeline(scenes):
    cursor = 0
    captions = []
    for scene in scenes:
        duration = scene.get("duration_seconds") or 6
        text = scene.get("caption") or ""
        captions.append({
            "scene_number": scene.get("scene_number"),
            "text": text,
            "start_seconds": cursor,
            "end_seconds": cursor + duration,
            "words": create_word_timings(text, cursor, duration),
        })
        cursor += duration
    return captions


def create_word_timings(text, start, duration):
    words = [word for word in re.split(r"\s+", text or "") if word]
    per_word = duration / len(words) if words else duration
    return [{
        "word": word,
        "start_seconds": round(start + index * per_word, 2),
        "end_seconds": round(start + (index + 1) * per_word, 2),
    } for index, word in enumerate(words)]


def estimate_scene_duration(text):
    words = len([word for word in re.split(r"\s+", text or "") if word])
    return min(10, max(5, math.ceil(words / 2.8)))


def create_short_title(text, fallback):
    clean = re.sub(r"[:.?!].*$", "", str(text or "")).strip()
    if not clean:
        return fallback
    words = " ".join(clean.split()[:5])
    return f"{words[:39].strip()}..." if len(words) > 42 else words


def detect_animation_type(lesson, scene):
    text = " ".join(str(value or "") for value in [
        lesson.get("subject"), lesson.get("chapter"), lesson.get("content_text"),
        scene.get("title"), scene.get("caption"), scene.get("visual_layout"),
    ]).lower()
    if "ionic" in text or "ion" in text or "bond" in text or "electron" in text:
        return "ionic_bond"
    if "photosynthesis" in text or "chlorophyll" in text:
        return "photosynthesis"
    if "food chain" in text or "producer" in text or "consumer" in text:
        return "food_chain"
    if "water cycle" in text or "evaporation" in text or "condensation" in text:
        return "water_cycle"
    if "solid" in text and "liquid" in text and "gas" in text:
        return "states_of_matter"
    if "circuit" in text or "electric" in text:
        return "electric_circuit"
    if "fraction" in text or "numerator" in text:
        return "fractions"
    if "root" in text or "stem" in text or "leaf" in text or "plant" in text:
        return "plant_parts"
    if "digestion" in text or "stomach" in text:
        return "digestion"
    return "default_concept"


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config
from .ai import generate_video_storyboard
from .database import create_record, filter_records, get_record, update_record
from .storage import upload_media, uses_s3
from .text_processing import split_sentences
from .tts import generate_narration_audio


def create_video_job_for_lesson(lesson_id: str, character: str = "maya", renderer: str = "cartoon"):
    lesson = get_record("lessons", lesson_id)
    scenes = build_storyboard_scenes(lesson)
    narration_text = "\n".join(scene.get("narration") or scene.get("caption") or "" for scene in scenes)
    captions = create_caption_timeline(scenes)
    renderer_choice = normalize_renderer(renderer)
    return create_record("video_jobs", {
        "lesson_id": lesson_id,
        "status": "storyboard_ready",
        "script": lesson.get("content_text") or "",
        "scenes": scenes,
        "narration_text": narration_text,
        "captions": captions,
        "provider_metadata": {
            "workflow": build_workflow(renderer_choice),
            "renderer": "huggingface_text_to_video",
            "renderer_choice": renderer_choice,
        },
    })


def get_latest_video_job_for_lesson(lesson_id: str):
    jobs = filter_records("video_jobs", {"lesson_id": lesson_id})
    return jobs[0] if jobs else None


def render_video_job(job_id: str):
    job = get_record("video_jobs", job_id)
    update_record("video_jobs", job_id, {"status": "rendering", "error_message": None})
    try:
        update_job_progress(job_id, job, "Preparing narration", 15)
        audio = generate_narration_audio(job_id, job.get("narration_text") or job.get("script") or "This lesson is ready.")
        if audio:
            update_record("video_jobs", job_id, {"audio_url": audio["audio_url"], "audio_status": "ready"})
        else:
            update_record("video_jobs", job_id, {"audio_status": "skipped"})

        job = get_record("video_jobs", job_id)
        output_file = config.RENDERS_DIR / f"{job_id}.mp4"
        renderer_choice = (job.get("provider_metadata") or {}).get("renderer_choice", "cartoon")
        if renderer_choice == "huggingface":
            update_job_progress(job_id, job, "Generating AI video with Hugging Face", 45)
            from .hf_video import render_huggingface_video
            hf_result = render_huggingface_video(
                job_id=job_id,
                job=job,
                output_file=output_file,
                audio_path=audio["audio_path"] if audio else None,
            )
        else:
            raise RuntimeError("Local character and Manim video generation are disabled. Use the Hugging Face renderer.")
        job = get_record("video_jobs", job_id)
        update_job_progress(job_id, job, "Finalizing MP4", 90)
        video_url = upload_media(output_file, "renders", f"{job_id}.mp4", "video/mp4")
        return update_record("video_jobs", job_id, {
            "status": "completed",
            "video_url": video_url,
            "provider_metadata": {
                **(job.get("provider_metadata") or {}),
                "hf_prompt": hf_result.get("prompt") if renderer_choice == "huggingface" else None,
                "hf_endpoint": hf_result.get("endpoint") if renderer_choice == "huggingface" else None,
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
            (config.RENDERS_DIR / f"{job_id}.mp4").unlink(missing_ok=True)
            (config.AUDIO_DIR / f"{job_id}.wav").unlink(missing_ok=True)


def update_job_progress(job_id: str, job: dict, label: str, percent: int):
    update_record("video_jobs", job_id, {
        "provider_metadata": {
            **(job.get("provider_metadata") or {}),
            "progress_label": label,
            "progress_percent": percent,
        }
    })


def render_moviepy_video(output_file: Path, title: str, scenes: list[dict], audio_path: Path | None, character: str = "maya"):
    try:
        from moviepy.editor import AudioFileClip, ImageSequenceClip, concatenate_videoclips
    except Exception as exc:
        raise RuntimeError("MoviePy is not installed. Run: pip install -r backend/requirements.txt") from exc

    safe_scenes = scenes or [{"title": title, "caption": "Lesson video", "duration_seconds": 5}]
    target_total = max(8, config.VIDEO_DURATION_SECONDS)
    scene_duration = max(3, target_total / len(safe_scenes))
    clips = []

    for index, scene in enumerate(safe_scenes):
        duration = scene.get("duration_seconds") or scene_duration
        frame_paths = create_scene_animation_frames(scene, index, len(safe_scenes), title, duration, character)
        clips.append(ImageSequenceClip([str(path) for path in frame_paths], fps=config.CARTOON_FRAME_FPS).set_duration(duration))

    video = concatenate_videoclips(clips, method="compose")
    if audio_path and Path(audio_path).exists():
        audio_clip = AudioFileClip(str(audio_path))
        video = video.set_audio(audio_clip)
        if audio_clip.duration and audio_clip.duration > video.duration:
            video = video.set_duration(audio_clip.duration)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(output_file),
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger=None,
    )


def create_scene_animation_frames(scene: dict, index: int, total: int, lesson_title: str, duration: float, character: str):
    frame_count = max(8, int(duration * config.CARTOON_FRAME_FPS))
    frame_paths = []
    scene_dir = config.VIDEO_FRAMES_DIR / safe_filename(lesson_title) / f"scene-{index + 1}"
    scene_dir.mkdir(parents=True, exist_ok=True)

    for frame_index in range(frame_count):
        progress = frame_index / max(1, frame_count - 1)
        frame_path = scene_dir / f"frame-{frame_index:04d}.png"
        create_scene_frame(scene, index, total, lesson_title, progress, frame_path, character)
        frame_paths.append(frame_path)

    return frame_paths


def create_scene_frame(scene: dict, index: int, total: int, lesson_title: str, progress: float, frame_path: Path, character: str):
    image = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), "#eff6ff")
    draw = ImageDraw.Draw(image)
    title_font = get_font(34)
    subtitle_font = get_font(20)
    body_font = get_font(26)
    small_font = get_font(18)
    tiny_font = get_font(15)

    draw.rounded_rectangle((36, 36, config.VIDEO_WIDTH - 36, config.VIDEO_HEIGHT - 36), radius=28, fill="#ffffff", outline="#bfdbfe", width=3)
    draw.text((64, 58), lesson_title[:42], fill="#1e3a8a", font=title_font)
    draw.text((64, 106), f"Scene {index + 1} of {total}", fill="#64748b", font=subtitle_font)

    scene_title = scene.get("title") or "Lesson Scene"
    caption = scene.get("caption") or scene.get("narration") or ""
    on_screen_text = normalize_on_screen_text(scene)

    draw_cartoon_classroom(draw, scene, on_screen_text, body_font, small_font, progress, character)

    draw_multiline_center(draw, scene_title, (70, 292, config.VIDEO_WIDTH - 70, 342), subtitle_font, "#0f172a")
    draw_multiline_center(draw, caption, (70, 348, config.VIDEO_WIDTH - 70, config.VIDEO_HEIGHT - 70), small_font, "#334155")
    draw.text((70, config.VIDEO_HEIGHT - 58), f"Cartoon scene: {truncate(scene.get('visual_layout') or scene.get('visual_prompt') or '', 110)}", fill="#64748b", font=tiny_font)
    image.save(frame_path)
    return frame_path


def draw_cartoon_classroom(draw, scene, on_screen_text, body_font, small_font, progress, character):
    visual_box = (74, 146, config.VIDEO_WIDTH - 74, 284)
    x1, y1, x2, y2 = visual_box
    draw.rounded_rectangle(visual_box, radius=26, fill="#f8fafc", outline="#c7d2fe", width=3)

    board_x1, board_y1, board_x2, board_y2 = x1 + 28, y1 + 18, x2 - 210, y2 - 18
    draw.rounded_rectangle((board_x1, board_y1, board_x2, board_y2), radius=18, fill="#ecfeff", outline="#67e8f9", width=3)
    draw.text((board_x1 + 18, board_y1 + 14), truncate(scene.get("title") or "Lesson", 34), fill="#155e75", font=get_font(22))

    draw_moving_concept_tokens(draw, on_screen_text, (board_x1 + 18, board_y1 + 50, board_x2 - 18, board_y2 - 10), progress, small_font)
    draw_cartoon_character(draw, x2 - 160, y2 - 22, progress, character)
    draw_speech_bubble(draw, x2 - 265, y1 + 12, truncate(scene.get("caption") or scene.get("narration") or "", 58), small_font, progress)
    draw_student_mascot(draw, x1 + 52, y2 - 12, progress)


def draw_moving_concept_tokens(draw, items, box, progress, font):
    x1, y1, x2, y2 = box
    colors = ["#dbeafe", "#dcfce7", "#fef3c7", "#f3e8ff", "#fee2e2"]
    for index, item in enumerate(items[:5]):
        row = index % 2
        col = index // 2
        left = x1 + col * 145 + int(10 * math.sin((progress * math.pi * 2) + index))
        top = y1 + row * 42 + int(6 * math.cos((progress * math.pi * 2) + index))
        right = min(left + 130, x2)
        draw.rounded_rectangle((left, top, right, top + 32), radius=14, fill=colors[index % len(colors)], outline="#bfdbfe", width=2)
        draw_multiline_center(draw, truncate(item, 20), (left + 8, top + 4, right - 8, top + 29), font, "#111827")


CHARACTER_STYLES = {
    "maya": {
        "skin": "#fed7aa",
        "hair": "#7c2d12",
        "body": "#ec4899",
        "body_outline": "#be185d",
        "shape": "human",
        "accessory": "lab",
    },
    "leo": {
        "skin": "#fde68a",
        "hair": "#1e3a8a",
        "body": "#2563eb",
        "body_outline": "#1d4ed8",
        "shape": "human",
        "accessory": "space",
    },
    "zara": {
        "skin": "#f5d0fe",
        "hair": "#581c87",
        "body": "#7c3aed",
        "body_outline": "#5b21b6",
        "shape": "human",
        "accessory": "teacher",
    },
    "kiko": {
        "skin": "#dbeafe",
        "hair": "#60a5fa",
        "body": "#10b981",
        "body_outline": "#047857",
        "shape": "robot",
        "accessory": "robot",
    },
    "milo_cat": {
        "skin": "#94a3b8",
        "hair": "#334155",
        "body": "#475569",
        "body_outline": "#1e293b",
        "shape": "cat",
        "accessory": "whiskers",
    },
    "pip_mouse": {
        "skin": "#fdba74",
        "hair": "#ea580c",
        "body": "#f97316",
        "body_outline": "#c2410c",
        "shape": "mouse",
        "accessory": "ears",
    },
    "captain_spinach": {
        "skin": "#fed7aa",
        "hair": "#1e3a8a",
        "body": "#0ea5e9",
        "body_outline": "#0369a1",
        "shape": "sailor",
        "accessory": "anchor",
    },
    "doodle_duck": {
        "skin": "#fde68a",
        "hair": "#f59e0b",
        "body": "#facc15",
        "body_outline": "#ca8a04",
        "shape": "duck",
        "accessory": "beak",
    },
}


def normalize_character(character):
    return character if character in CHARACTER_STYLES else "maya"


def normalize_renderer(renderer):
    return "huggingface"


def build_workflow(renderer):
    return ["LLM storyboard", "educational text-to-video prompt", "CogVideoX/custom video API generation", "Kokoro narration", "MoviePy audio mux", "MP4 render"]


def draw_cartoon_character(draw, x, ground_y, progress, character):
    style = CHARACTER_STYLES.get(normalize_character(character), CHARACTER_STYLES["maya"])
    if style["shape"] == "robot":
        draw_robot_character(draw, x, ground_y, progress, style)
    elif style["shape"] == "cat":
        draw_cat_character(draw, x, ground_y, progress, style)
    elif style["shape"] == "mouse":
        draw_mouse_character(draw, x, ground_y, progress, style)
    elif style["shape"] == "sailor":
        draw_sailor_character(draw, x, ground_y, progress, style)
    elif style["shape"] == "duck":
        draw_duck_character(draw, x, ground_y, progress, style)
    else:
        draw_human_character(draw, x, ground_y, progress, style)


def draw_human_character(draw, x, ground_y, progress, style):
    bob = int(8 * math.sin(progress * math.pi * 2))
    wave = int(10 * math.sin(progress * math.pi * 4))
    head_y = ground_y - 104 + bob

    draw.ellipse((x - 36, head_y - 36, x + 36, head_y + 36), fill=style["skin"], outline="#fb923c", width=3)
    draw.arc((x - 24, head_y - 10, x - 8, head_y + 8), 200, 340, fill="#111827", width=2)
    draw.arc((x + 8, head_y - 10, x + 24, head_y + 8), 200, 340, fill="#111827", width=2)
    draw.arc((x - 14, head_y + 8, x + 14, head_y + 26), 0, 180, fill="#111827", width=3)
    draw.pieslice((x - 38, head_y - 42, x + 38, head_y - 2), 180, 360, fill=style["hair"])

    body_top = ground_y - 66 + bob
    draw.rounded_rectangle((x - 34, body_top, x + 34, ground_y - 12 + bob), radius=18, fill=style["body"], outline=style["body_outline"], width=3)
    draw.line((x - 28, body_top + 14, x - 62, body_top + 42), fill=style["skin"], width=8)
    draw.line((x + 28, body_top + 14, x + 60, body_top + 22 + wave), fill=style["skin"], width=8)
    draw.line((x - 16, ground_y - 12 + bob, x - 28, ground_y), fill="#1e293b", width=8)
    draw.line((x + 16, ground_y - 12 + bob, x + 28, ground_y), fill="#1e293b", width=8)
    draw.ellipse((x + 52, body_top + 14 + wave, x + 68, body_top + 30 + wave), fill=style["skin"])

    if style["accessory"] == "lab":
        draw.line((x - 18, body_top + 8, x - 8, ground_y - 18 + bob), fill="#ffffff", width=4)
        draw.line((x + 18, body_top + 8, x + 8, ground_y - 18 + bob), fill="#ffffff", width=4)
        draw.ellipse((x + 6, body_top + 24, x + 16, body_top + 34), fill="#fef08a")
    elif style["accessory"] == "space":
        draw.ellipse((x - 45, head_y - 45, x + 45, head_y + 45), outline="#bfdbfe", width=4)
        draw.rectangle((x - 20, body_top + 20, x + 20, body_top + 34), fill="#dbeafe", outline="#1d4ed8")
    elif style["accessory"] == "teacher":
        draw.line((x + 62, body_top + 22 + wave, x + 82, body_top + 10 + wave), fill="#92400e", width=4)
        draw.text((x - 18, body_top + 17), "A+", fill="#ffffff", font=get_font(14))


def draw_robot_character(draw, x, ground_y, progress, style):
    bob = int(6 * math.sin(progress * math.pi * 2))
    wave = int(12 * math.sin(progress * math.pi * 4))
    head_y = ground_y - 104 + bob
    draw.rounded_rectangle((x - 38, head_y - 34, x + 38, head_y + 34), radius=14, fill=style["skin"], outline=style["hair"], width=4)
    draw.line((x, head_y - 34, x, head_y - 52), fill=style["hair"], width=4)
    draw.ellipse((x - 7, head_y - 60, x + 7, head_y - 46), fill="#facc15")
    draw.ellipse((x - 22, head_y - 8, x - 8, head_y + 6), fill="#0f172a")
    draw.ellipse((x + 8, head_y - 8, x + 22, head_y + 6), fill="#0f172a")
    draw.arc((x - 16, head_y + 10, x + 16, head_y + 24), 0, 180, fill="#0f172a", width=3)

    body_top = ground_y - 66 + bob
    draw.rounded_rectangle((x - 36, body_top, x + 36, ground_y - 10 + bob), radius=12, fill=style["body"], outline=style["body_outline"], width=4)
    draw.ellipse((x - 10, body_top + 18, x + 10, body_top + 38), fill="#facc15")
    draw.line((x - 32, body_top + 16, x - 62, body_top + 38), fill=style["hair"], width=8)
    draw.line((x + 32, body_top + 16, x + 62, body_top + 22 + wave), fill=style["hair"], width=8)
    draw.rectangle((x + 56, body_top + 16 + wave, x + 72, body_top + 32 + wave), fill="#dbeafe", outline=style["hair"])
    draw.line((x - 16, ground_y - 10 + bob, x - 28, ground_y), fill="#1e293b", width=8)
    draw.line((x + 16, ground_y - 10 + bob, x + 28, ground_y), fill="#1e293b", width=8)


def draw_cat_character(draw, x, ground_y, progress, style):
    bob = int(7 * math.sin(progress * math.pi * 2))
    wave = int(10 * math.sin(progress * math.pi * 4))
    head_y = ground_y - 104 + bob
    draw.polygon([(x - 32, head_y - 25), (x - 18, head_y - 58), (x - 5, head_y - 27)], fill=style["skin"], outline=style["body_outline"])
    draw.polygon([(x + 32, head_y - 25), (x + 18, head_y - 58), (x + 5, head_y - 27)], fill=style["skin"], outline=style["body_outline"])
    draw.ellipse((x - 38, head_y - 38, x + 38, head_y + 38), fill=style["skin"], outline=style["body_outline"], width=4)
    draw.ellipse((x - 18, head_y - 8, x - 8, head_y + 4), fill="#0f172a")
    draw.ellipse((x + 8, head_y - 8, x + 18, head_y + 4), fill="#0f172a")
    draw.polygon([(x - 4, head_y + 8), (x + 4, head_y + 8), (x, head_y + 14)], fill="#fca5a5")
    for offset in [-14, 0, 14]:
        draw.line((x - 4, head_y + 16, x - 48, head_y + offset), fill="#0f172a", width=2)
        draw.line((x + 4, head_y + 16, x + 48, head_y + offset), fill="#0f172a", width=2)
    body_top = ground_y - 66 + bob
    draw.rounded_rectangle((x - 34, body_top, x + 34, ground_y - 10 + bob), radius=22, fill=style["body"], outline=style["body_outline"], width=4)
    draw.line((x + 28, body_top + 12, x + 62, body_top + 22 + wave), fill=style["skin"], width=8)
    draw.arc((x - 58, ground_y - 72 + bob, x - 8, ground_y - 18 + bob), 80, 250, fill=style["body_outline"], width=6)
    draw.line((x - 16, ground_y - 10 + bob, x - 28, ground_y), fill="#1e293b", width=8)
    draw.line((x + 16, ground_y - 10 + bob, x + 28, ground_y), fill="#1e293b", width=8)


def draw_mouse_character(draw, x, ground_y, progress, style):
    bob = int(7 * math.sin(progress * math.pi * 2))
    wave = int(10 * math.sin(progress * math.pi * 4))
    head_y = ground_y - 104 + bob
    draw.ellipse((x - 58, head_y - 58, x - 18, head_y - 18), fill=style["skin"], outline=style["body_outline"], width=4)
    draw.ellipse((x + 18, head_y - 58, x + 58, head_y - 18), fill=style["skin"], outline=style["body_outline"], width=4)
    draw.ellipse((x - 38, head_y - 38, x + 38, head_y + 38), fill="#fed7aa", outline=style["body_outline"], width=4)
    draw.ellipse((x - 16, head_y - 8, x - 6, head_y + 4), fill="#0f172a")
    draw.ellipse((x + 6, head_y - 8, x + 16, head_y + 4), fill="#0f172a")
    draw.ellipse((x - 5, head_y + 8, x + 5, head_y + 18), fill="#f97316")
    draw.arc((x - 14, head_y + 14, x + 14, head_y + 28), 0, 180, fill="#0f172a", width=2)
    body_top = ground_y - 66 + bob
    draw.rounded_rectangle((x - 32, body_top, x + 32, ground_y - 10 + bob), radius=20, fill=style["body"], outline=style["body_outline"], width=4)
    draw.line((x + 28, body_top + 12, x + 62, body_top + 22 + wave), fill="#fed7aa", width=8)
    draw.arc((x - 64, ground_y - 58 + bob, x - 8, ground_y - 10 + bob), 100, 270, fill=style["body_outline"], width=5)
    draw.line((x - 14, ground_y - 10 + bob, x - 24, ground_y), fill="#1e293b", width=7)
    draw.line((x + 14, ground_y - 10 + bob, x + 24, ground_y), fill="#1e293b", width=7)


def draw_sailor_character(draw, x, ground_y, progress, style):
    draw_human_character(draw, x, ground_y, progress, style)
    bob = int(8 * math.sin(progress * math.pi * 2))
    head_y = ground_y - 104 + bob
    draw.rounded_rectangle((x - 30, head_y - 58, x + 30, head_y - 40), radius=8, fill="#ffffff", outline="#1e3a8a", width=3)
    draw.rectangle((x - 14, head_y - 72, x + 14, head_y - 52), fill="#ffffff", outline="#1e3a8a")
    draw.text((x - 10, ground_y - 48 + bob), "⚓", fill="#ffffff", font=get_font(18))


def draw_duck_character(draw, x, ground_y, progress, style):
    bob = int(7 * math.sin(progress * math.pi * 2))
    wing = int(12 * math.sin(progress * math.pi * 4))
    head_y = ground_y - 104 + bob
    draw.ellipse((x - 38, head_y - 38, x + 38, head_y + 38), fill=style["skin"], outline=style["body_outline"], width=4)
    draw.polygon([(x - 8, head_y + 4), (x + 48, head_y + 12), (x - 8, head_y + 24)], fill="#fb923c", outline="#c2410c")
    draw.ellipse((x - 14, head_y - 10, x - 5, head_y - 1), fill="#0f172a")
    draw.ellipse((x + 8, head_y - 10, x + 17, head_y - 1), fill="#0f172a")
    body_top = ground_y - 66 + bob
    draw.ellipse((x - 38, body_top, x + 38, ground_y - 4 + bob), fill=style["body"], outline=style["body_outline"], width=4)
    draw.ellipse((x + 18, body_top + 14 + wing, x + 58, body_top + 48 + wing), fill="#fde68a", outline=style["body_outline"], width=3)
    draw.line((x - 14, ground_y - 8 + bob, x - 26, ground_y), fill="#fb923c", width=7)
    draw.line((x + 14, ground_y - 8 + bob, x + 26, ground_y), fill="#fb923c", width=7)


def draw_student_mascot(draw, x, ground_y, progress):
    bob = int(6 * math.cos(progress * math.pi * 2))
    head_y = ground_y - 62 + bob
    draw.ellipse((x - 24, head_y - 24, x + 24, head_y + 24), fill="#bfdbfe", outline="#60a5fa", width=3)
    draw.ellipse((x - 10, head_y - 5, x - 4, head_y + 1), fill="#0f172a")
    draw.ellipse((x + 4, head_y - 5, x + 10, head_y + 1), fill="#0f172a")
    draw.arc((x - 10, head_y + 4, x + 10, head_y + 16), 0, 180, fill="#0f172a", width=2)
    draw.rounded_rectangle((x - 24, ground_y - 38 + bob, x + 24, ground_y - 4 + bob), radius=14, fill="#22c55e", outline="#16a34a", width=3)
    draw.line((x - 14, ground_y - 4 + bob, x - 20, ground_y), fill="#1e293b", width=5)
    draw.line((x + 14, ground_y - 4 + bob, x + 20, ground_y), fill="#1e293b", width=5)


def draw_speech_bubble(draw, x, y, text, font, progress):
    if progress < 0.08:
        return
    pulse = int(3 * math.sin(progress * math.pi * 4))
    box = (x, y + pulse, x + 170, y + 76 + pulse)
    draw.rounded_rectangle(box, radius=18, fill="#ffffff", outline="#93c5fd", width=3)
    draw.polygon([(x + 132, y + 76 + pulse), (x + 150, y + 96 + pulse), (x + 154, y + 76 + pulse)], fill="#ffffff", outline="#93c5fd")
    draw_multiline_center(draw, text, (x + 12, y + 8 + pulse, x + 158, y + 68 + pulse), font, "#1e293b")


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
    for index, scene in enumerate(storyboard_scenes[:7]):
        narration = scene.get("narration") or scene.get("caption") or scene.get("title") or ""
        caption = scene.get("caption") or narration
        scenes.append({
            "scene_number": index + 1,
            "title": scene.get("title") or f"Scene {index + 1}",
            "caption": caption,
            "narration": narration,
            "visual_prompt": scene.get("image_prompt") or scene.get("visual_layout") or "Educational slide visual.",
            "visual_layout": scene.get("visual_layout") or scene.get("image_prompt") or "Educational slide visual.",
            "on_screen_text": sanitize_text_list(scene.get("on_screen_text")),
            "image_prompt": scene.get("image_prompt") or "",
            "animation_type": detect_animation_type(lesson, scene),
            "duration_seconds": estimate_scene_duration(narration or caption),
            "avatar_clip_url": None,
            "broll_clip_url": None,
        })
    return scenes


def sanitize_text_list(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:5]


def normalize_on_screen_text(scene: dict):
    items = sanitize_text_list(scene.get("on_screen_text"))
    if len(items) >= 3:
        return items[:5]
    keywords = get_keywords(f"{scene.get('title') or ''} {scene.get('caption') or ''} {scene.get('visual_layout') or scene.get('visual_prompt') or ''}")
    for keyword in keywords:
        if keyword not in items:
            items.append(keyword)
        if len(items) >= 3:
            break
    while len(items) < 3:
        items.append(["Main concept", "Key detail", "Remember"][len(items)])
    return items[:5]


def draw_storyboard_visual(draw, scene, on_screen_text, body_font, small_font):
    card_y = 158
    visual_box = (74, card_y, config.VIDEO_WIDTH - 74, 280)
    draw.rounded_rectangle(visual_box, radius=26, fill="#f8fafc", outline="#c7d2fe", width=3)

    if len(on_screen_text) <= 3:
        draw_connected_cards(draw, on_screen_text[:3], body_font, visual_box)
    else:
        draw_bullet_board(draw, on_screen_text, small_font, visual_box)


def draw_connected_cards(draw, items, font, visual_box):
    x1, y1, x2, y2 = visual_box
    card_w = min(190, (x2 - x1 - 70) // 3)
    gap = ((x2 - x1) - card_w * 3) // 4
    card_h = 82
    top = y1 + 27
    colors = ["#dbeafe", "#dcfce7", "#fef3c7"]
    outlines = ["#60a5fa", "#4ade80", "#facc15"]
    centers = []

    for index, item in enumerate(items):
        left = x1 + gap + index * (card_w + gap)
        right = left + card_w
        centers.append(((left + right) // 2, top + card_h // 2))
        draw.rounded_rectangle((left, top, right, top + card_h), radius=20, fill=colors[index], outline=outlines[index], width=4)
        draw_multiline_center(draw, truncate(item, 34), (left + 10, top + 14, right - 10, top + card_h - 12), font, "#111827")

    for left, right in zip(centers, centers[1:]):
        draw.line((left[0] + card_w // 2, left[1], right[0] - card_w // 2, right[1]), fill="#2563eb", width=6)


def draw_bullet_board(draw, items, font, visual_box):
    x1, y1, x2, y2 = visual_box
    draw.text((x1 + 28, y1 + 20), "What to notice:", fill="#1e3a8a", font=get_font(22))
    y = y1 + 55
    for item in items[:5]:
        draw.ellipse((x1 + 32, y + 8, x1 + 42, y + 18), fill="#2563eb")
        draw.text((x1 + 55, y), truncate(item, 64), fill="#111827", font=font)
        y += 27


def draw_multiline_center(draw, text, box, font, fill):
    x1, y1, x2, y2 = box
    lines = wrap_text(text, font, x2 - x1, draw)[:4]
    line_height = font.size + 6
    total_h = len(lines) * line_height
    y = y1 + max(0, ((y2 - y1) - total_h) // 2)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text((x1 + ((x2 - x1) - (bbox[2] - bbox[0])) / 2, y), line, fill=fill, font=font)
        y += line_height


def wrap_text(text, font, max_width, draw):
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def get_font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def safe_filename(value):
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "lesson").strip("-")[:60] or "lesson"


def truncate(value, limit):
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:max(0, limit - 3)].strip()}..."


def build_scenes_from_lesson(lesson: dict):
    key_points = [item for item in (lesson.get("key_points") or []) if item]
    content_sentences = split_sentences(lesson.get("content_text") or "")
    main_points = key_points or content_sentences[:5]
    vocabulary = [item for item in (lesson.get("vocabulary") or []) if item.get("word")]
    lesson_title = " - ".join(filter(None, [lesson.get("subject"), lesson.get("chapter")])) or lesson.get("chapter") or "Lesson"

    scenes = [{
        "title": lesson.get("chapter") or "Lesson Introduction",
        "caption": f"Today we are learning {lesson_title}.",
        "visual": f"Show the title {lesson_title} with simple icons connected to the main concept.",
        "narration": f"Today we are learning {lesson_title}.",
    }]

    for index, point in enumerate(main_points[:4]):
        scenes.append({
            "title": create_short_title(point, f"Key Idea {index + 1}"),
            "caption": point,
            "visual": f"Visualize this exact idea: {point}",
            "narration": point,
        })

    if vocabulary:
        words = "; ".join(f"{item.get('word')}: {item.get('definition') or 'important term'}" for item in vocabulary[:3])
        scenes.append({"title": "Important Words", "caption": words, "visual": f"Show vocabulary cards for: {words}", "narration": words})

    scenes.append({
        "title": "Quick Review",
        "caption": f"Review {lesson.get('chapter') or 'this lesson'} and try the quiz to check your understanding.",
        "visual": "Show a checklist, flashcard, and quiz card for review.",
        "narration": f"Review {lesson.get('chapter') or 'this lesson'} and try the quiz to check your understanding.",
    })

    return [{
        "scene_number": index + 1,
        "title": scene.get("title"),
        "caption": scene.get("caption"),
        "narration": scene.get("narration") or scene.get("caption"),
        "visual_prompt": scene.get("visual") or "Simple accessible classroom animation.",
        "visual_layout": scene.get("visual") or "Simple accessible classroom animation.",
        "on_screen_text": normalize_on_screen_text({
            "title": scene.get("title"),
            "caption": scene.get("caption"),
            "visual_layout": scene.get("visual"),
        }),
        "image_prompt": scene.get("visual") or "",
        "animation_type": detect_animation_type(lesson, scene),
        "duration_seconds": estimate_scene_duration(scene.get("narration") or scene.get("caption") or ""),
        "avatar_clip_url": None,
        "broll_clip_url": None,
    } for index, scene in enumerate(scenes[:7])]


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
    return min(12, max(5, math.ceil(words / 2.4)))


def create_short_title(text, fallback):
    clean = re.sub(r"[:.?!].*$", "", str(text or "")).strip()
    if not clean:
        return fallback
    words = " ".join(clean.split()[:5])
    return f"{words[:39].strip()}..." if len(words) > 42 else words


def detect_animation_type(lesson, scene):
    text = " ".join(str(value or "") for value in [
        lesson.get("subject"), lesson.get("chapter"), lesson.get("content_text"), scene.get("title"), scene.get("caption")
    ]).lower()
    if "ionic" in text or "ion" in text or "bond" in text:
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


def get_keywords(text):
    stop_words = {"about", "after", "also", "and", "are", "because", "for", "from", "has", "have", "important", "learn", "learning", "lesson", "show", "simple", "that", "the", "this", "today", "try", "understand", "with"}
    words = re.sub(r"[^a-zA-Z0-9\s-]", " ", text or "").split()
    unique = []
    for word in words:
        if len(word) > 3 and word.lower() not in stop_words and word not in unique:
            unique.append(word[:18])
    return unique

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config


def render_manim_video(job_id: str, job: dict, output_file: Path, audio_path: Path | None = None):
    scenes = normalize_manim_scenes(job.get("scenes") or [])
    title = (job.get("lesson_contents") or {}).get("chapter") or "UDL Lesson"
    job_dir = config.MANIM_JOBS_DIR / job_id
    media_dir = job_dir / "media"
    script_path = job_dir / "lesson_animation.py"
    job_dir.mkdir(parents=True, exist_ok=True)
    script_path.write_text(build_manim_script(title, scenes), encoding="utf-8")

    quality = normalize_quality(config.MANIM_QUALITY)
    command = [
        sys.executable,
        "-m",
        "manim",
        f"-q{quality}",
        str(script_path),
        "UDLLessonScene",
        "--media_dir",
        str(media_dir),
        "--output_file",
        f"{job_id}.mp4",
        "--disable_caching",
    ]
    log_path = job_dir / "manim-render.log"
    error_path = job_dir / "manim-render.err.log"
    child_env = os.environ.copy()
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"

    try:
        with log_path.open("w", encoding="utf-8") as stdout_file, error_path.open("w", encoding="utf-8") as stderr_file:
            result = subprocess.run(
                command,
                cwd=str(job_dir),
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                env=child_env,
                timeout=config.MANIM_RENDER_TIMEOUT_SECONDS,
                check=False,
            )
    except FileNotFoundError as exc:
        raise RuntimeError("Python could not start Manim. Reinstall backend dependencies with: pip install -r requirements.txt") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Manim rendering timed out after {config.MANIM_RENDER_TIMEOUT_SECONDS} seconds. Try MANIM_QUALITY=l or a faster server.") from exc

    if result.returncode != 0:
        error_text = read_tail(error_path) or read_tail(log_path)
        if "No module named manim" in error_text:
            raise RuntimeError("Manim is not installed in this Python environment. Run: pip install -r requirements.txt")
        raise RuntimeError(f"Manim render failed: {error_text[-1800:]}")

    rendered_file = find_rendered_mp4(media_dir, job_id)
    if not rendered_file:
        raise RuntimeError("Manim finished but no MP4 file was found in the media folder.")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(rendered_file, output_file)

    if audio_path and Path(audio_path).exists():
        attach_audio(output_file, Path(audio_path))

    return output_file


def normalize_manim_scenes(scenes: list[dict]):
    safe_scenes = scenes or [{"title": "Lesson", "caption": "Let us learn this idea step by step.", "on_screen_text": ["Idea", "Example", "Practice"]}]
    normalized = []
    for index, scene in enumerate(safe_scenes[:7]):
        text_items = scene.get("on_screen_text") or []
        if not isinstance(text_items, list):
            text_items = []
        if len(text_items) < 3:
            text_items = [scene.get("title") or "Idea", "Example", "Practice"]
        normalized.append({
            "title": clean_text(scene.get("title") or f"Scene {index + 1}", 48),
            "caption": clean_text(scene.get("caption") or scene.get("narration") or "", 140),
            "items": [clean_text(item, 24) for item in text_items[:4]],
            "duration": max(2, min(6, int(scene.get("duration_seconds") or 4))),
            "animation_type": clean_text(scene.get("animation_type") or "default_concept", 32),
        })
    return normalized


def build_manim_script(title: str, scenes: list[dict]):
    payload = json.dumps({
        "title": clean_text(title, 56),
        "scenes": scenes,
        "width": config.VIDEO_WIDTH,
        "height": config.VIDEO_HEIGHT,
    }, ensure_ascii=False)
    return f'''
from manim import *

PAYLOAD = {payload!r}
DATA = __import__("json").loads(PAYLOAD)


class UDLLessonScene(Scene):
    def construct(self):
        self.camera.background_color = "#eef6ff"
        lesson_title = Text(DATA["title"], font_size=30, color=BLUE_E, weight=BOLD).to_edge(UP)
        self.play(FadeIn(lesson_title, shift=DOWN), run_time=0.5)
        for index, scene in enumerate(DATA["scenes"]):
            self.play(*[FadeOut(mob) for mob in self.mobjects if mob is not lesson_title], run_time=0.25)
            self.render_scene(scene, index + 1, len(DATA["scenes"]))
        self.play(FadeOut(*self.mobjects), run_time=0.4)

    def render_scene(self, scene, number, total):
        scene_label = Text(f"Scene {{number}} of {{total}}", font_size=20, color=GRAY).to_corner(UL)
        title = Text(scene["title"], font_size=34, color=BLUE_E, weight=BOLD).next_to(scene_label, DOWN, aligned_edge=LEFT)
        caption = Text(scene["caption"], font_size=20, color=DARK_GRAY, line_spacing=0.85).scale_to_fit_width(11).to_edge(DOWN)
        diagram = self.create_diagram(scene).move_to(ORIGIN + UP * 0.15)
        self.play(FadeIn(scene_label), Write(title), run_time=0.7)
        self.play(LaggedStart(*[GrowFromCenter(mob) for mob in diagram], lag_ratio=0.14), run_time=1.4)
        self.play(FadeIn(caption, shift=UP * 0.2), run_time=0.5)
        self.wait(scene.get("duration", 4))

    def create_diagram(self, scene):
        items = scene.get("items") or ["Idea", "Example", "Practice"]
        colors = [BLUE_C, GREEN_C, YELLOW_C, PURPLE_C]
        group = VGroup()
        nodes = VGroup()
        arrows = VGroup()
        spacing = min(3.3, 9 / max(1, len(items)))
        start_x = -spacing * (len(items) - 1) / 2

        for i, item in enumerate(items):
            x = start_x + i * spacing
            shape = Circle(radius=0.82, color=colors[i % len(colors)], fill_color=colors[i % len(colors)], fill_opacity=0.22)
            if i % 2 == 1:
                shape = RoundedRectangle(width=2.0, height=1.35, corner_radius=0.22, color=colors[i % len(colors)], fill_color=colors[i % len(colors)], fill_opacity=0.22)
            label = Text(item, font_size=19, color=BLACK, weight=BOLD).scale_to_fit_width(1.75)
            node = VGroup(shape, label).move_to([x, 0, 0])
            nodes.add(node)
            if i > 0:
                arrows.add(Arrow(nodes[i - 1].get_right(), node.get_left(), buff=0.18, color=BLUE_E, stroke_width=5))

        topic = scene.get("animation_type", "")
        accent = self.topic_accent(topic)
        accent.next_to(nodes, UP, buff=0.55)
        group.add(accent, nodes, arrows)
        return group

    def topic_accent(self, topic):
        if "ionic" in topic or "bond" in topic:
            left = Circle(radius=0.36, color=BLUE, fill_opacity=0.4)
            right = Circle(radius=0.36, color=GREEN, fill_opacity=0.4).shift(RIGHT * 2.2)
            electron = Dot(color=YELLOW).move_to(left.get_right() + RIGHT * 0.25)
            arrow = CurvedArrow(left.get_right(), right.get_left(), color=YELLOW_E)
            label = Text("electron transfer", font_size=18, color=BLUE_E).next_to(arrow, UP)
            return VGroup(left, right, electron, arrow, label)
        if "plant" in topic or "photosynthesis" in topic:
            stem = Line(DOWN * 0.5, UP * 0.45, color=GREEN_E, stroke_width=8)
            leaf1 = Ellipse(width=0.75, height=0.38, color=GREEN, fill_opacity=0.45).shift(LEFT * 0.35 + UP * 0.05).rotate(0.5)
            leaf2 = Ellipse(width=0.75, height=0.38, color=GREEN, fill_opacity=0.45).shift(RIGHT * 0.35 + UP * 0.18).rotate(-0.5)
            sun = Circle(radius=0.25, color=YELLOW, fill_opacity=0.7).shift(LEFT * 1.4 + UP * 0.55)
            return VGroup(sun, stem, leaf1, leaf2)
        return VGroup(Text("Animated concept map", font_size=20, color=BLUE_E), SurroundingRectangle(Text(""), color=BLUE_E, buff=0.1).set_opacity(0))
'''


def find_rendered_mp4(media_dir: Path, job_id: str):
    if not media_dir.exists():
        return None
    matches = sorted(media_dir.rglob(f"{job_id}.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
    if matches:
        return matches[0]
    all_mp4 = sorted(media_dir.rglob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
    return all_mp4[0] if all_mp4 else None


def read_tail(path: Path, limit: int = 2400):
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return text[-limit:]


def attach_audio(video_file: Path, audio_path: Path):
    try:
        from moviepy.editor import AudioFileClip, VideoFileClip
    except Exception as exc:
        raise RuntimeError("MoviePy is required to attach narration audio to the Manim video.") from exc

    temp_output = video_file.with_name(f"{video_file.stem}-with-audio.mp4")
    video_clip = VideoFileClip(str(video_file))
    audio_clip = AudioFileClip(str(audio_path))
    final_clip = video_clip.set_duration(max(video_clip.duration, audio_clip.duration)).set_audio(audio_clip)
    final_clip.write_videofile(
        str(temp_output),
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger=None,
    )
    video_clip.close()
    audio_clip.close()
    final_clip.close()
    temp_output.replace(video_file)


def normalize_quality(value: str):
    value = (value or "l").strip().lower()
    aliases = {
        "low": "l",
        "low_quality": "l",
        "medium": "m",
        "medium_quality": "m",
        "high": "h",
        "high_quality": "h",
    }
    return aliases.get(value, value if value in {"k", "p", "h", "m", "l"} else "l")


def clean_text(value, limit: int):
    text = " ".join(str(value or "").replace("\n", " ").split())
    return text[:limit].strip() or "Lesson"

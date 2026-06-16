import json
from pathlib import Path

import requests

from . import config


def render_huggingface_video(job_id: str, job: dict, output_file: Path, audio_path: Path | None = None):
    endpoint = get_hf_endpoint()
    prompt = build_video_prompt(job)
    payload = {
        "inputs": prompt,
        "parameters": {
            "num_frames": config.HF_VIDEO_NUM_FRAMES,
            "guidance_scale": config.HF_VIDEO_GUIDANCE_SCALE,
        },
        "options": {
            "wait_for_model": True,
        },
    }
    headers = {
        "Accept": "video/mp4,application/json",
        "Content-Type": "application/json",
    }
    if config.VIDEO_API_ENDPOINT and config.VIDEO_API_TOKEN:
        headers["Authorization"] = f"Bearer {config.VIDEO_API_TOKEN}"
    elif config.HF_TOKEN:
        headers["Authorization"] = f"Bearer {config.HF_TOKEN}"

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=config.HF_VIDEO_TIMEOUT_SECONDS,
        )
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Could not connect to Hugging Face. Your computer/server cannot resolve or reach the Hugging Face API host. "
            "Check internet, DNS, VPN/proxy/firewall, or set HF_VIDEO_ENDPOINT to a reachable paid Hugging Face Inference Endpoint."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            f"Hugging Face video generation timed out after {config.HF_VIDEO_TIMEOUT_SECONDS} seconds. "
            "Increase HF_VIDEO_TIMEOUT_SECONDS or use a dedicated Inference Endpoint."
        ) from exc

    if response.status_code >= 400:
        raise RuntimeError(format_hf_error(response))

    content_type = response.headers.get("content-type", "").lower()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if "video" in content_type or response.content[:8].startswith(b"\x00\x00\x00"):
        output_file.write_bytes(response.content)
    else:
        data = parse_json_response(response)
        video_url = data.get("video_url") or data.get("url") or data.get("output")
        if isinstance(video_url, list):
            video_url = video_url[0] if video_url else None
        if not video_url:
            raise RuntimeError(f"Hugging Face did not return a video file. Response: {json.dumps(data)[:800]}")
        download_video(video_url, output_file)

    if audio_path and Path(audio_path).exists():
        attach_audio(output_file, Path(audio_path))

    return {
        "output_file": output_file,
        "prompt": prompt,
        "endpoint": endpoint,
    }


def get_hf_endpoint():
    if config.VIDEO_API_ENDPOINT:
        return config.VIDEO_API_ENDPOINT
    if config.HF_VIDEO_ENDPOINT:
        return config.HF_VIDEO_ENDPOINT
    if not config.HF_TOKEN:
        raise RuntimeError("No video API is configured. Add VIDEO_API_ENDPOINT for your CogVideoX server, or add HF_TOKEN for Hugging Face.")
    if not config.HF_VIDEO_MODEL:
        raise RuntimeError("HF_VIDEO_MODEL is missing. Add a Hugging Face text-to-video model id to backend/.env.")
    return f"https://api-inference.huggingface.co/models/{config.HF_VIDEO_MODEL}"


def build_video_prompt(job: dict):
    lesson = job.get("lesson_contents") or {}
    scenes = job.get("scenes") or []
    title = lesson.get("chapter") or "UDL lesson"
    subject = lesson.get("subject") or "school subject"
    scene_lines = []
    for scene in scenes[:4]:
        scene_lines.append(
            f"{scene.get('title') or 'Concept'}: {scene.get('visual_layout') or scene.get('visual_prompt') or scene.get('caption') or ''}"
        )
    scene_text = " ".join(scene_lines)[:1200]
    return (
        f"High quality educational animated video for students in classes 5 to 10. "
        f"Subject: {subject}. Lesson: {title}. "
        f"Show clear visual explanations, smooth camera motion, colorful classroom-friendly animation, "
        f"simple scientific objects and diagrams, no copyrighted characters, no logos, no confusing text. "
        f"Visual plan: {scene_text}"
    ).strip()


def download_video(url: str, output_file: Path):
    response = requests.get(url, timeout=config.HF_VIDEO_TIMEOUT_SECONDS)
    if response.status_code >= 400:
        raise RuntimeError(f"Could not download generated Hugging Face video: HTTP {response.status_code}")
    output_file.write_bytes(response.content)


def attach_audio(video_file: Path, audio_path: Path):
    try:
        from moviepy.editor import AudioFileClip, VideoFileClip
    except Exception as exc:
        raise RuntimeError("MoviePy is required to attach narration audio to the Hugging Face video.") from exc

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


def parse_json_response(response):
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:800]}


def format_hf_error(response):
    try:
        data = response.json()
        message = data.get("error") or data.get("message") or json.dumps(data)
    except Exception:
        message = response.text
    if response.status_code == 401:
        return "Hugging Face rejected the request. Check HF_TOKEN in backend/.env."
    if response.status_code == 404:
        return "Hugging Face model/endpoint not found. Check HF_VIDEO_MODEL or HF_VIDEO_ENDPOINT in backend/.env."
    if response.status_code in {429, 503}:
        return f"Hugging Face video service is busy or rate-limited ({response.status_code}). Try again later or use a paid Inference Endpoint. Details: {message[:500]}"
    return f"Hugging Face video generation failed ({response.status_code}): {message[:800]}"

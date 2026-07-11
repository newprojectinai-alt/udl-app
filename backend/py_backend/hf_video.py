import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin

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

    if config.VIDEO_API_MODE == "async":
        render_async_video(endpoint, headers, payload, output_file)
    else:
        render_sync_video(endpoint, headers, payload, output_file)

    if audio_path and Path(audio_path).exists():
        attach_audio(output_file, Path(audio_path))

    normalize_mp4_for_browser(output_file)

    return {
        "output_file": output_file,
        "prompt": prompt,
        "endpoint": endpoint,
    }


def render_sync_video(endpoint: str, headers: dict, payload: dict, output_file: Path):
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

    save_video_response(response, output_file)


def render_async_video(endpoint: str, headers: dict, payload: dict, output_file: Path):
    request_timeout = min(config.VIDEO_API_REQUEST_TIMEOUT_SECONDS, config.HF_VIDEO_TIMEOUT_SECONDS)
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=request_timeout)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Could not submit the CogVideoX job: {exc}") from exc

    if response.status_code >= 400:
        raise RuntimeError(format_hf_error(response))

    job_data = parse_json_response(response)
    job_id = job_data.get("id") or job_data.get("job_id")
    if not job_id:
        raise RuntimeError(f"CogVideoX did not return a job id. Response: {json.dumps(job_data)[:800]}")

    status_url = absolute_api_url(endpoint, job_data.get("status_url") or f"{endpoint.rstrip('/')}/{job_id}")
    result_url = job_data.get("result_url")
    deadline = time.monotonic() + config.HF_VIDEO_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        remaining = max(1, int(deadline - time.monotonic()))
        try:
            status_response = requests.get(
                status_url,
                headers=headers,
                timeout=min(config.VIDEO_API_REQUEST_TIMEOUT_SECONDS, remaining),
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Could not check CogVideoX job {job_id}: {exc}") from exc

        if status_response.status_code >= 400:
            raise RuntimeError(format_hf_error(status_response))

        status_data = parse_json_response(status_response)
        status = str(status_data.get("status") or "").lower()
        result_url = status_data.get("result_url") or result_url

        if status in {"completed", "succeeded", "success"}:
            if not result_url:
                result_url = f"{endpoint.rstrip('/')}/{job_id}/result"
            download_video(absolute_api_url(endpoint, result_url), output_file, headers=headers)
            return
        if status in {"failed", "error", "cancelled"}:
            message = status_data.get("error") or status_data.get("message") or "Unknown GPU worker error"
            raise RuntimeError(f"CogVideoX job {job_id} failed: {message}")

        time.sleep(min(config.VIDEO_API_POLL_SECONDS, max(1, remaining)))

    raise RuntimeError(
        f"CogVideoX job {job_id} timed out after {config.HF_VIDEO_TIMEOUT_SECONDS} seconds."
    )


def absolute_api_url(endpoint: str, value: str):
    if value.startswith(("http://", "https://")):
        return value
    return urljoin(f"{endpoint.rstrip('/')}/", value)


def save_video_response(response: requests.Response, output_file: Path):
    content_type = response.headers.get("content-type", "").lower()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if "video" in content_type or response.content[:8].startswith(b"\x00\x00\x00"):
        output_file.write_bytes(response.content)
        return

    data = parse_json_response(response)
    video_url = data.get("video_url") or data.get("url") or data.get("output")
    if isinstance(video_url, list):
        video_url = video_url[0] if video_url else None
    if not video_url:
        raise RuntimeError(f"Video provider did not return a video file. Response: {json.dumps(data)[:800]}")
    download_video(video_url, output_file)


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


def download_video(url: str, output_file: Path, headers: dict | None = None):
    response = requests.get(
        url,
        headers=headers or {},
        timeout=min(config.HF_VIDEO_TIMEOUT_SECONDS, 300),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Could not download generated video: HTTP {response.status_code}")
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


def normalize_mp4_for_browser(video_file: Path):
    normalized_output = video_file.with_name(f"{video_file.stem}-browser.mp4")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_file),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(normalized_output),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required to prepare generated videos for browser playback.") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Could not prepare generated video for browser playback: {details[-800:]}") from exc
    normalized_output.replace(video_file)


def parse_json_response(response):
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:800]}


def format_hf_error(response):
    provider_name = "CogVideoX" if config.VIDEO_API_ENDPOINT else "Hugging Face"
    try:
        data = response.json()
        message = data.get("error") or data.get("message") or json.dumps(data)
    except Exception:
        message = response.text
    if response.status_code == 401:
        token_name = "VIDEO_API_TOKEN" if config.VIDEO_API_ENDPOINT else "HF_TOKEN"
        return f"{provider_name} rejected the request. Check {token_name} in backend/.env."
    if response.status_code == 404:
        return f"{provider_name} endpoint was not found. Check the configured video endpoint."
    if response.status_code in {429, 503}:
        return f"{provider_name} is busy or rate-limited ({response.status_code}). Details: {message[:500]}"
    return f"{provider_name} video generation failed ({response.status_code}): {message[:800]}"

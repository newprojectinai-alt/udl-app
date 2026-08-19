import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

from . import config


def render_huggingface_video(job_id: str, job: dict, output_file: Path, audio_path: Path | None = None):
    endpoint = get_hf_endpoint()
    headers = {
        "Accept": "video/mp4,application/json",
        "Content-Type": "application/json",
    }
    if config.VIDEO_API_ENDPOINT and config.VIDEO_API_TOKEN:
        headers["Authorization"] = f"Bearer {config.VIDEO_API_TOKEN}"
    elif config.HF_TOKEN:
        headers["Authorization"] = f"Bearer {config.HF_TOKEN}"

    prompts = build_scene_video_prompts(job) if config.HF_VIDEO_RENDER_SCENES else [build_video_prompt(job)]
    if len(prompts) == 1:
        render_provider_video(endpoint, headers, build_video_payload(prompts[0], 0), output_file)
    else:
        render_scene_clips(endpoint, headers, prompts, output_file)
    validate_video_file(output_file, "CogVideoX downloaded output")

    if audio_path and Path(audio_path).exists():
        attach_audio(output_file, Path(audio_path))
        validate_video_file(output_file, "audio muxed output")

    normalize_mp4_for_browser(output_file)
    validate_video_file(output_file, "browser-ready output")

    return {
        "output_file": output_file,
        "prompt": prompts[0],
        "prompts": prompts,
        "scene_count": len(prompts),
        "endpoint": endpoint,
        "output_bytes": output_file.stat().st_size,
    }


def build_video_payload(prompt: str, scene_index: int):
    return {
        "inputs": prompt,
        "parameters": {
            "num_frames": config.HF_VIDEO_NUM_FRAMES,
            "num_inference_steps": config.HF_VIDEO_NUM_STEPS,
            "guidance_scale": config.HF_VIDEO_GUIDANCE_SCALE,
            "seed": (int(time.time()) + scene_index * 7919) % 2147483647,
        },
        "options": {
            "wait_for_model": True,
        },
    }


def render_provider_video(endpoint: str, headers: dict, payload: dict, output_file: Path):
    if config.VIDEO_API_MODE == "async":
        render_async_video(endpoint, headers, payload, output_file)
    else:
        render_sync_video(endpoint, headers, payload, output_file)


def render_scene_clips(endpoint: str, headers: dict, prompts: list[str], output_file: Path):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    scene_dir = output_file.with_suffix("")
    scene_dir.mkdir(parents=True, exist_ok=True)
    clip_paths = []
    try:
        for index, prompt in enumerate(prompts):
            clip_path = scene_dir / f"scene-{index + 1:02d}.mp4"
            render_provider_video(endpoint, headers, build_video_payload(prompt, index), clip_path)
            validate_video_file(clip_path, f"CogVideoX scene {index + 1} output")
            clip_paths.append(clip_path)
        concatenate_videos(clip_paths, output_file)
    finally:
        for clip_path in clip_paths:
            clip_path.unlink(missing_ok=True)
        try:
            scene_dir.rmdir()
        except OSError:
            pass


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
        validate_video_file(output_file, "provider response")
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
    for scene in scenes[:3]:
        scene_lines.append(
            f"{scene.get('title') or 'Concept'} — {scene.get('visual_layout') or scene.get('visual_prompt') or scene.get('caption') or ''}"
        )
    scene_text = " | ".join(scene_lines)[:1000]
    return (
        f"Create a short 6-second educational animation, not a slideshow or title card. "
        f"Topic: {subject} - {title}. "
        f"Use a colorful high-contrast 2D/3D animation style with visible scientific objects filling the frame, diagrams, arrows, "
        f"particles, icons, and smooth motion. Use saturated blue, orange, green, and purple on a non-white background. "
        f"Show one continuous visual explanation of the concept with moving objects. "
        f"Avoid white screens, black screens, blank frames, empty slides, watermarks, logos, copyrighted characters, realistic faces, and tiny unreadable text. "
        f"Use simple labels only if they are large and legible. "
        f"Visual content to animate: {scene_text}"
    ).strip()


def build_scene_video_prompts(job: dict):
    lesson = job.get("lesson_contents") or {}
    scenes = (job.get("scenes") or [])[:config.HF_VIDEO_MAX_SCENES]
    if not scenes:
        return [build_video_prompt(job)]

    title = lesson.get("chapter") or "UDL lesson"
    subject = lesson.get("subject") or "school subject"
    prompts = []
    for index, scene in enumerate(scenes):
        visual_text = scene.get("visual_layout") or scene.get("visual_prompt") or scene.get("image_prompt") or scene.get("caption") or ""
        narration = scene.get("narration") or scene.get("caption") or ""
        on_screen_text = ", ".join(scene.get("on_screen_text") or [])
        prompts.append((
            f"Create scene {index + 1} of a textbook-based educational video for Class {lesson.get('class_level') or ''} {subject}, chapter {title}. "
            f"Teach this exact concept clearly: {scene.get('title') or title}. "
            f"Visual explanation: {visual_text}. "
            f"Narration meaning to support visually: {narration}. "
            f"Use high-contrast colorful 2D/3D educational animation, visible objects filling the frame, arrows, diagrams, particles, icons, and smooth motion. "
            f"Use saturated blue, orange, green, and purple on a non-white background. "
            f"Include only these large readable labels if useful: {on_screen_text}. "
            f"Do not create a blank screen, white slide, title card only, static poster, watermark, logo, realistic face, or tiny unreadable text. "
            f"Make the frame teach the concept visually even without audio."
        ).strip()[:1800])
    return prompts


def download_video(url: str, output_file: Path, headers: dict | None = None):
    response = requests.get(
        url,
        headers=headers or {},
        timeout=min(config.HF_VIDEO_TIMEOUT_SECONDS, 300),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Could not download generated video: HTTP {response.status_code}")
    output_file.write_bytes(response.content)
    validate_video_file(output_file, "downloaded CogVideoX result")


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


def concatenate_videos(clip_paths: list[Path], output_file: Path):
    if not clip_paths:
        raise RuntimeError("No scene clips were generated.")

    list_file = output_file.with_name(f"{output_file.stem}-clips.txt")
    normalized_paths = []
    try:
        for index, clip_path in enumerate(clip_paths):
            normalized_path = output_file.with_name(f"{output_file.stem}-scene-{index + 1:02d}-normalized.mp4")
            normalize_clip_for_concat(clip_path, normalized_path)
            normalized_paths.append(normalized_path)

        list_file.write_text(
            "\n".join(f"file '{path.as_posix()}'" for path in normalized_paths),
            encoding="utf-8",
        )
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_file),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required to stitch scene videos together.") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Could not stitch generated scene videos: {details[-800:]}") from exc
    finally:
        list_file.unlink(missing_ok=True)
        for normalized_path in normalized_paths:
            normalized_path.unlink(missing_ok=True)


def normalize_clip_for_concat(input_file: Path, output_file: Path):
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-an",
        "-vf",
        "scale=720:480:force_original_aspect_ratio=decrease,pad=720:480:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=8",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        str(output_file),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)


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


def validate_video_file(video_file: Path, stage: str):
    if not video_file.is_file():
        raise RuntimeError(f"{stage} did not create an MP4 file.")

    size = video_file.stat().st_size
    if size < config.HF_VIDEO_MIN_BYTES:
        raise RuntimeError(
            f"{stage} is too small to be a valid generated video ({size} bytes). "
            "This usually means the GPU worker produced a blank/header-only MP4. "
            "Check the RunPod job diagnostics/logs, model load status, CUDA memory, and CogVideoX output."
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,nb_frames,duration",
        "-of",
        "json",
        str(video_file),
    ]
    try:
        probe = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        return
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"{stage} is not a readable MP4 video: {details[-500:]}") from exc

    try:
        streams = json.loads(probe.stdout or "{}").get("streams") or []
    except Exception:
        streams = []
    if not streams:
        raise RuntimeError(f"{stage} does not contain a video stream.")


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

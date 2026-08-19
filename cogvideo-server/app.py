import json
import os
import threading
import time
from pathlib import Path
from uuid import uuid4

import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from PIL import ImageStat
from pydantic import BaseModel


MODEL_ID = os.getenv("COGVIDEO_MODEL_ID", "zai-org/CogVideoX-5b")
API_TOKEN = os.getenv("VIDEO_API_TOKEN", "")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
NUM_FRAMES = int(os.getenv("COGVIDEO_NUM_FRAMES", "49"))
NUM_STEPS = int(os.getenv("COGVIDEO_NUM_STEPS", "35"))
GUIDANCE_SCALE = float(os.getenv("COGVIDEO_GUIDANCE_SCALE", "6.0"))
MIN_VIDEO_BYTES = max(10240, int(os.getenv("COGVIDEO_MIN_VIDEO_BYTES", "100000")))
MAX_ATTEMPTS = max(1, int(os.getenv("COGVIDEO_MAX_ATTEMPTS", "2")))
BLANK_STDDEV_THRESHOLD = float(os.getenv("COGVIDEO_BLANK_STDDEV_THRESHOLD", "1.0"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOB_DIR = OUTPUT_DIR / "jobs"
JOB_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CogVideoX Server")
pipe = None
generation_lock = threading.Lock()
job_state_lock = threading.Lock()


class VideoRequest(BaseModel):
    inputs: str
    parameters: dict | None = None


@app.on_event("startup")
def load_model():
    global pipe
    if not torch.cuda.is_available():
        raise RuntimeError("CogVideoX requires an NVIDIA CUDA GPU")
    pipe = CogVideoXPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()


@app.get("/health")
def health():
    return {
        "ok": True,
        "model": MODEL_ID,
        "cuda": torch.cuda.is_available(),
        "model_loaded": pipe is not None,
    }


@app.post("/generate")
def generate_video(request: VideoRequest, authorization: str | None = Header(default=None)):
    authorize(authorization)
    validate_request(request)

    output_path = OUTPUT_DIR / f"{uuid4().hex}.mp4"
    with generation_lock:
        render_video(request.inputs, request.parameters or {}, output_path)
    return FileResponse(str(output_path), media_type="video/mp4", filename="lesson-video.mp4")


@app.post("/jobs", status_code=202)
def create_video_job(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    authorize(authorization)
    validate_request(request)

    job_id = uuid4().hex
    write_job(job_id, {
        "id": job_id,
        "status": "queued",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "error": None,
    })
    background_tasks.add_task(
        run_video_job,
        job_id,
        request.inputs,
        request.parameters or {},
    )
    return public_job(read_job(job_id))


@app.get("/jobs/{job_id}")
def get_video_job(job_id: str, authorization: str | None = Header(default=None)):
    authorize(authorization)
    return public_job(read_job(job_id))


@app.get("/jobs/{job_id}/result")
def get_video_job_result(job_id: str, authorization: str | None = Header(default=None)):
    authorize(authorization)
    job = read_job(job_id)
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail=f"Video job is {job.get('status')}")

    output_path = JOB_DIR / f"{job_id}.mp4"
    if not output_path.is_file():
        raise HTTPException(status_code=404, detail="Generated video file not found")
    return FileResponse(str(output_path), media_type="video/mp4", filename="lesson-video.mp4")


def authorize(authorization: str | None):
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid VIDEO_API_TOKEN")


def validate_request(request: VideoRequest):
    if not request.inputs.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")


def run_video_job(job_id: str, prompt: str, params: dict):
    with generation_lock:
        write_job(job_id, {"status": "running", "updated_at": int(time.time())})
        try:
            output_path = JOB_DIR / f"{job_id}.mp4"
            diagnostics = render_video(prompt, params, output_path)
            write_job(job_id, {
                "status": "completed",
                "updated_at": int(time.time()),
                "error": None,
                "diagnostics": diagnostics,
            })
        except Exception as exc:
            write_job(job_id, {
                "status": "failed",
                "updated_at": int(time.time()),
                "error": str(exc),
            })


def render_video(prompt: str, params: dict, output_path: Path):
    if pipe is None:
        raise RuntimeError("CogVideoX model is not loaded")

    seed = int(params.get("seed", 42))
    num_inference_steps = int(params.get("num_inference_steps", NUM_STEPS))
    num_frames = int(params.get("num_frames", NUM_FRAMES))
    guidance_scale = float(params.get("guidance_scale", GUIDANCE_SCALE))

    attempts = []
    last_frames = None
    last_prompt = prompt
    last_seed = seed
    for attempt_index in range(MAX_ATTEMPTS):
        attempt_seed = seed + (attempt_index * 101)
        attempt_prompt = build_attempt_prompt(prompt, attempt_index)
        generator = torch.Generator(device="cuda").manual_seed(attempt_seed)
        frames = pipe(
            prompt=attempt_prompt[:1800],
            num_videos_per_prompt=1,
            num_inference_steps=num_inference_steps,
            num_frames=num_frames,
            guidance_scale=guidance_scale,
            generator=generator,
        ).frames[0]
        frame_diagnostics = inspect_frames(frames)
        attempts.append({
            "attempt": attempt_index + 1,
            "seed": attempt_seed,
            "frame_diagnostics": frame_diagnostics,
            "prompt_excerpt": attempt_prompt[:500],
        })
        last_frames = frames
        last_prompt = attempt_prompt
        last_seed = attempt_seed
        if frame_diagnostics["sample_average_stddev"] >= BLANK_STDDEV_THRESHOLD:
            break
    else:
        raise RuntimeError(f"CogVideoX produced near-blank frames after {MAX_ATTEMPTS} attempts: {attempts}")

    frames = last_frames
    frame_diagnostics = attempts[-1]["frame_diagnostics"]

    export_to_video(frames, str(output_path), fps=8)
    output_bytes = output_path.stat().st_size if output_path.is_file() else 0
    if output_bytes < MIN_VIDEO_BYTES:
        raise RuntimeError(
            f"CogVideoX exported a tiny invalid MP4 ({output_bytes} bytes). "
            f"Frame diagnostics: {frame_diagnostics}"
        )
    return {
        "output_bytes": output_bytes,
        "frame_count": len(frames),
        "parameters": {
            "seed": seed,
            "actual_seed": last_seed,
            "num_frames": num_frames,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
        },
        "frame_diagnostics": frame_diagnostics,
        "attempts": attempts,
        "prompt_excerpt": last_prompt[:500],
    }


def build_attempt_prompt(prompt: str, attempt_index: int):
    visual_guard = (
        "High contrast colorful educational animation with visible objects filling the frame. "
        "Use saturated blue, orange, green, and purple shapes on a non-white background. "
        "Show clear motion, arrows, diagrams, particles, icons, and large simple objects. "
        "Do not produce a blank white screen, plain background, empty slide, title card only, or faded low-contrast image. "
    )
    if attempt_index == 0:
        return f"{visual_guard}{prompt}"
    return (
        f"{visual_guard}"
        "Retry with a simpler concrete scene: animated classroom science diagram, colorful labeled objects, "
        "moving arrows, particles interacting, camera slowly pushes in. "
        f"Lesson request: {prompt}"
    )


def inspect_frames(frames):
    if not frames:
        raise RuntimeError("CogVideoX returned zero frames")
    sample_indexes = sorted(set([0, len(frames) // 2, len(frames) - 1]))
    samples = []
    for index in sample_indexes:
        frame = frames[index].convert("RGB")
        stat = ImageStat.Stat(frame)
        average_stddev = sum(stat.stddev) / len(stat.stddev)
        samples.append({
            "index": index,
            "size": list(frame.size),
            "mean": [round(value, 3) for value in stat.mean],
            "stddev": [round(value, 3) for value in stat.stddev],
            "average_stddev": round(average_stddev, 3),
        })
    return {
        "sample_count": len(samples),
        "sample_average_stddev": round(sum(item["average_stddev"] for item in samples) / len(samples), 3),
        "samples": samples,
    }


def job_metadata_path(job_id: str):
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job id")
    return JOB_DIR / f"{job_id}.json"


def read_job(job_id: str):
    metadata_path = job_metadata_path(job_id)
    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Video job not found")
    with job_state_lock:
        return json.loads(metadata_path.read_text(encoding="utf-8"))


def write_job(job_id: str, values: dict):
    metadata_path = job_metadata_path(job_id)
    with job_state_lock:
        current = {}
        if metadata_path.is_file():
            current = json.loads(metadata_path.read_text(encoding="utf-8"))
        current.update(values)
        temporary_path = metadata_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(current), encoding="utf-8")
        temporary_path.replace(metadata_path)
    return current


def public_job(job: dict):
    job_id = job["id"]
    result = {
        "id": job_id,
        "status": job.get("status"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "error": job.get("error"),
        "status_url": f"/jobs/{job_id}",
    }
    if job.get("status") == "completed":
        result["result_url"] = f"/jobs/{job_id}/result"
    if job.get("diagnostics"):
        result["diagnostics"] = job.get("diagnostics")
    return result

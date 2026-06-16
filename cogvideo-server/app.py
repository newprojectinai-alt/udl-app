import os
from pathlib import Path
from uuid import uuid4

import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


MODEL_ID = os.getenv("COGVIDEO_MODEL_ID", "zai-org/CogVideoX-5b")
API_TOKEN = os.getenv("VIDEO_API_TOKEN", "")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
NUM_FRAMES = int(os.getenv("COGVIDEO_NUM_FRAMES", "49"))
NUM_STEPS = int(os.getenv("COGVIDEO_NUM_STEPS", "35"))
GUIDANCE_SCALE = float(os.getenv("COGVIDEO_GUIDANCE_SCALE", "6.0"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CogVideoX Server")
pipe = None


class VideoRequest(BaseModel):
    inputs: str
    parameters: dict | None = None


@app.on_event("startup")
def load_model():
    global pipe
    pipe = CogVideoXPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_ID, "cuda": torch.cuda.is_available()}


@app.post("/generate")
def generate_video(request: VideoRequest, authorization: str | None = Header(default=None)):
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid VIDEO_API_TOKEN")
    if not request.inputs.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    params = request.parameters or {}
    output_path = OUTPUT_DIR / f"{uuid4().hex}.mp4"
    generator = torch.Generator(device="cuda").manual_seed(int(params.get("seed", 42)))
    frames = pipe(
        prompt=request.inputs[:1800],
        num_videos_per_prompt=1,
        num_inference_steps=int(params.get("num_inference_steps", NUM_STEPS)),
        num_frames=int(params.get("num_frames", NUM_FRAMES)),
        guidance_scale=float(params.get("guidance_scale", GUIDANCE_SCALE)),
        generator=generator,
    ).frames[0]
    export_to_video(frames, str(output_path), fps=8)
    return FileResponse(str(output_path), media_type="video/mp4", filename="lesson-video.mp4")

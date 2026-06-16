# CogVideoX-5B GPU Server

This optional service runs `zai-org/CogVideoX-5b` on your rented RTX 4090 server and exposes a small API used by the main UDL backend.

## Minimum Practical Server

- NVIDIA RTX 4090 with 24 GB VRAM
- Ubuntu 22.04/24.04 recommended
- NVIDIA driver installed
- CUDA-compatible PyTorch
- 32 GB system RAM minimum, 64 GB better
- 80 GB+ free disk for model cache and outputs
- Python 3.10 or 3.11

CogVideoX-5B can run on a 24 GB card with `diffusers` CPU offload and VAE tiling, but it will be slow. Expect several minutes per short video on a 4090.

## Install

```bash
cd cogvideo-server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Install CUDA PyTorch if the default install does not detect your GPU:

```bash
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision
```

## Run

```bash
export VIDEO_API_TOKEN="choose-a-long-random-secret"
export COGVIDEO_MODEL_ID="zai-org/CogVideoX-5b"
export COGVIDEO_NUM_STEPS=35
export COGVIDEO_NUM_FRAMES=49
uvicorn app:app --host 0.0.0.0 --port 8000
```

Health check:

```txt
http://YOUR_SERVER_IP:8000/health
```

## Connect Main Backend

In `backend/.env` on your main app:

```env
VIDEO_API_ENDPOINT=http://YOUR_SERVER_IP:8000/generate
VIDEO_API_TOKEN=choose-a-long-random-secret
HF_VIDEO_MODEL=zai-org/CogVideoX-5b
```

Restart the main backend after changing `.env`.

## Production Notes

- Put this behind HTTPS before giving public access.
- Use a firewall so only your backend can call port `8000`.
- Do not expose this GPU API directly to students.
- Queue requests if more than one student may render at the same time.

import subprocess
import wave
import struct
from pathlib import Path

from . import config


def write_silent_wav(output_path: Path, duration_seconds: float = 2.0, sample_rate: int = 24000):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_samples = int(duration_seconds * sample_rate)
    with wave.open(str(output_path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for _ in range(total_samples):
            wav.writeframes(struct.pack("<h", 0))


def generate_narration_audio(job_id: str, text: str):
    output_path = config.AUDIO_DIR / f"{job_id}.wav"
    if config.SKIP_TTS:
        return None

    script_path = config.BACKEND_ROOT / "tts" / "kokoro_tts.py"
    try:
        subprocess.run(
            [
                config.PYTHON_COMMAND,
                str(script_path),
                "--text",
                text or "This lesson is ready.",
                "--output",
                str(output_path),
                "--voice",
                config.KOKORO_VOICE,
                "--fallback-silence",
            ],
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        )
    except Exception as exc:
        print(f"Kokoro TTS failed; writing silence: {exc}")
        write_silent_wav(output_path)

    return {
        "audio_path": output_path,
        "audio_url": f"/audio/{job_id}.wav",
    }

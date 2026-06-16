import argparse
import wave
import struct
from pathlib import Path


def write_silent_wav(output_path: str, duration_seconds: float = 2.0, sample_rate: int = 24000):
    total_samples = int(duration_seconds * sample_rate)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(output_path, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for _ in range(total_samples):
            wav.writeframes(struct.pack("<h", 0))


def synthesize_with_kokoro(text: str, output_path: str, voice: str):
    try:
        from kokoro import KPipeline
        import soundfile as sf
    except Exception as exc:
        raise RuntimeError(
            "Kokoro is not installed. Install it in a Python environment, then rerun TTS."
        ) from exc

    pipeline = KPipeline(lang_code="a")
    generator = pipeline(text, voice=voice, speed=1.0)
    audio_chunks = []
    sample_rate = 24000

    for _, _, audio in generator:
        audio_chunks.append(audio)

    if not audio_chunks:
        write_silent_wav(output_path)
        return

    try:
        import numpy as np
        audio = np.concatenate(audio_chunks)
    except Exception:
        audio = audio_chunks[0]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, sample_rate)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--fallback-silence", action="store_true")
    args = parser.parse_args()

    try:
        synthesize_with_kokoro(args.text, args.output, args.voice)
    except Exception as exc:
        if args.fallback_silence:
            print(f"Kokoro unavailable, writing silent placeholder: {exc}")
            write_silent_wav(args.output)
        else:
            raise


if __name__ == "__main__":
    main()

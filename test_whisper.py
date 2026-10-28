import sys
import time

from faster_whisper import WhisperModel

# Usage: python test_whisper.py <audio_file> [model_size] [language|auto] [prompt|noprompt]
# Example: python test_whisper.py test1.m4a small
#          python test_whisper.py test1.m4a small auto noprompt
#          python test_whisper.py test1.m4a small hi
audio_path = sys.argv[1]
model_size = sys.argv[2] if len(sys.argv) > 2 else "small"
language = None if len(sys.argv) <= 3 or sys.argv[3] == "auto" else sys.argv[3]
use_prompt = not (len(sys.argv) > 4 and sys.argv[4] == "noprompt")

PROMPT = "Namaste, how are you? Main theek hoon. Aaj meeting hai, let's start."

print(f"Loading model '{model_size}'...")
t0 = time.time()
model = WhisperModel(model_size, device="cpu", compute_type="int8")
print(f"Model loaded in {time.time() - t0:.1f}s")

t0 = time.time()
segments, info = model.transcribe(
    audio_path,
    language=language,
    task="transcribe",
    beam_size=5,
    vad_filter=True,
    initial_prompt=PROMPT if use_prompt else None,
)
print(f"Detected language: {info.language} ({info.language_probability:.2f})")

parts = []
for seg in segments:
    print(f"[{seg.start:.1f}s -> {seg.end:.1f}s] {seg.text}")
    parts.append(seg.text.strip())

print(f"Transcribed in {time.time() - t0:.1f}s")
print("FULL TEXT:", " ".join(parts))
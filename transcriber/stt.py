import io
import os
import threading
import wave

import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

SAMPLE_RATE = 16000

# STT_BACKEND=local -> faster-whisper on this machine (self-hosted, default)
# STT_BACKEND=groq  -> Whisper large-v3 hosted by Groq (used for the deployed demo)
STT_BACKEND = os.environ.get("STT_BACKEND", "local").lower()

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")
BEAM_SIZE = int(os.environ.get("WHISPER_BEAM", "1"))

GROQ_MODEL = os.environ.get("GROQ_MODEL", "whisper-large-v3")
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Short priming prompts. They steer which script the model writes in.
PROMPT_HINDI = "नमस्ते दोस्तों, आज हम टेक्नोलॉजी और बिज़नेस के बारे में बात करेंगे।"
PROMPT_HINGLISH = (
    "Namaste dosto, aaj hum technology aur business ke baare mein baat karenge. "
    "Okay, let's start."
)

# mode -> (whisper language, initial prompt)
#   mix: Hindi + English in Roman script (Hinglish)
#   hi:  Hindi in Devanagari
#   en:  English
MODES = {
    "mix": ("en", PROMPT_HINGLISH),
    "hi": ("hi", PROMPT_HINDI),
    "en": ("en", None),
}

_model = None
_load_lock = threading.Lock()
_infer_lock = threading.Lock()


def get_model():
    """Load the local Whisper model once. Does nothing for the hosted backend."""
    global _model
    if STT_BACKEND != "local":
        return None
    if _model is None:
        with _load_lock:
            if _model is None:
                from faster_whisper import WhisperModel

                _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _norm(text):
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _transcribe_local(audio, language, prompt):
    model = get_model()
    with _infer_lock:
        segments, info = model.transcribe(
            audio,
            language=language,
            task="transcribe",
            beam_size=BEAM_SIZE,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=prompt,
            repetition_penalty=1.1,           # reduces "same phrase repeated" loops
            compression_ratio_threshold=2.0,  # retries decoding when output is repetitive
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
    return text, info.language, info.language_probability


def _to_wav_bytes(audio):
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()


def _transcribe_groq(audio, language, prompt):
    import requests

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    data = {"model": GROQ_MODEL, "response_format": "json", "temperature": "0"}
    if language:
        data["language"] = language
    if prompt:
        data["prompt"] = prompt

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("audio.wav", _to_wav_bytes(audio), "audio/wav")},
        data=data,
        timeout=30,
    )
    if response.status_code == 429:
        raise RuntimeError("Speech API rate limit reached. Wait a minute and try again.")
    if not response.ok:
        raise RuntimeError(f"Speech API error {response.status_code}: {response.text[:200]}")

    text = response.json().get("text", "").strip()
    return text, language or "auto", 1.0


def transcribe_audio(audio: np.ndarray, language=None, prompt=None):
    """audio: float32 numpy array, 16 kHz mono. Returns (text, language, probability)."""
    if STT_BACKEND == "groq":
        text, lang, prob = _transcribe_groq(audio, language, prompt)
    else:
        text, lang, prob = _transcribe_local(audio, language, prompt)

    # Prompt echo filter: drop the output if the model just copied the prompt.
    if prompt and text:
        n, p = _norm(text), _norm(prompt)
        if len(n) >= 15 and (n in p or p in n):
            text = ""

    return text, lang, prob
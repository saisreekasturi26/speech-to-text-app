import asyncio
import json
from urllib.parse import parse_qs

import numpy as np
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.urls import reverse
from django.utils import timezone

from .models import Transcription
from .stt import MODES, SAMPLE_RATE, get_model, transcribe_audio

ENERGY_THRESHOLD = 0.01   # audio louder than this counts as speech
SILENCE_END_SEC = 0.8     # silence length that ends a phrase
MAX_SEGMENT_SEC = 12      # maximum length of one phrase
MIN_SPEECH_SEC = 0.4      # shorter speech is ignored


class TranscribeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query = parse_qs(self.scope["query_string"].decode())
        mode = query.get("lang", ["mix"])[0]
        if mode not in MODES:
            mode = "mix"
        self.mode = mode
        self.language, self.prompt = MODES[mode]

        self.lines = []      # phrases transcribed in this session
        self.saved = False   # whether the session is already stored in the database

        self.queue = asyncio.Queue()
        self.reset_state()
        await self.accept()
        await self.send_payload({"type": "status", "message": "Loading speech model..."})
        self.worker = asyncio.create_task(self.worker_loop())

    async def disconnect(self, close_code):
        worker = getattr(self, "worker", None)
        if worker:
            worker.cancel()
        # If the tab was closed mid-session, save what we have (no-op if already saved).
        if hasattr(self, "lines"):
            try:
                await self.save_session()
            except Exception:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            if len(bytes_data) % 2:
                bytes_data = bytes_data[:-1]
            samples = np.frombuffer(bytes_data, dtype=np.int16).astype(np.float32) / 32768.0
            if len(samples):
                self.handle_audio(samples)
        elif text_data:
            try:
                message = json.loads(text_data)
            except ValueError:
                return
            if message.get("type") == "stop":
                self.flush_segment()
                self.queue.put_nowait(None)  # tells the worker the session is over

    # ---------- audio handling ----------
    def reset_state(self):
        self.buffer = []
        self.buffer_samples = 0
        self.voiced_samples = 0
        self.silence_samples = 0
        self.in_speech = False
        self.preroll = None

    def handle_audio(self, samples):
        rms = float(np.sqrt(np.mean(samples ** 2)))
        voiced = rms > ENERGY_THRESHOLD

        if voiced:
            if not self.in_speech:
                self.in_speech = True
                self.buffer = []
                self.buffer_samples = 0
                if self.preroll is not None:  # keep a little audio from before speech started
                    self.buffer.append(self.preroll)
                    self.buffer_samples += len(self.preroll)
            self.buffer.append(samples)
            self.buffer_samples += len(samples)
            self.voiced_samples += len(samples)
            self.silence_samples = 0
        elif self.in_speech:
            self.buffer.append(samples)
            self.buffer_samples += len(samples)
            self.silence_samples += len(samples)
        else:
            self.preroll = samples

        if self.in_speech and (
            self.silence_samples >= SILENCE_END_SEC * SAMPLE_RATE
            or self.buffer_samples >= MAX_SEGMENT_SEC * SAMPLE_RATE
        ):
            self.flush_segment()

    def flush_segment(self):
        if self.in_speech and self.voiced_samples >= MIN_SPEECH_SEC * SAMPLE_RATE:
            self.queue.put_nowait(np.concatenate(self.buffer))
        self.reset_state()

    # ---------- saving to the database ----------
    @database_sync_to_async
    def _create_record(self, text):
        stamp = timezone.localtime().strftime("%d %b %Y, %H:%M")
        return Transcription.objects.create(
            title=f"Live - {stamp}",
            text=text,
            language=self.mode,
        )

    async def save_session(self):
        """Store the session text as one record. Nothing is saved if no speech was found."""
        if self.saved:
            return None
        self.saved = True
        text = "\n".join(self.lines).strip()
        if not text:
            return None
        return await self._create_record(text)

    # ---------- transcription worker ----------
    async def worker_loop(self):
        try:
            await asyncio.to_thread(get_model)
            await self.send_payload({"type": "ready"})
            while True:
                audio = await self.queue.get()
                if audio is None:
                    payload = {"type": "done", "saved": False}
                    try:
                        record = await self.save_session()
                        if record is not None:
                            payload["saved"] = True
                            payload["id"] = record.pk
                            payload["url"] = reverse("transcriber:detail", args=[record.pk])
                    except Exception as exc:
                        payload["error"] = f"Could not save: {exc}"
                    await self.send_payload(payload)
                    return
                try:
                    text, language, prob = await asyncio.to_thread(
                        transcribe_audio, audio, self.language, self.prompt
                    )
                except Exception as exc:
                    await self.send_payload({"type": "error", "message": str(exc)})
                    continue
                if text:
                    self.lines.append(text)
                    await self.send_payload({
                        "type": "final",
                        "text": text,
                        "language": language,
                        "probability": round(float(prob), 2),
                    })
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self.send_payload({"type": "error", "message": f"Model load failed: {exc}"})

    async def send_payload(self, payload):
        await self.send(text_data=json.dumps(payload))
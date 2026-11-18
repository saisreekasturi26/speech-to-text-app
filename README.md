# Speech to Text

A web application that transcribes speech in real time, including mixed Hindi and English speech. Each session is stored in PostgreSQL and can be managed from a dashboard with full CRUD operations.

**Live demo:** https://speech-to-text-app-110k.onrender.com
(Free hosting: the app sleeps when idle, so the first load can take about a minute.)

## Features

- Real-time transcription from the browser microphone over WebSockets
- Three language modes: **Hindi + English Mix** (Roman script), **Hindi** (Devanagari), **English**
- Each Start/Stop session is saved automatically as one record
- Dashboard with search, pagination, and create / view / edit / delete

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Django, Django Channels (ASGI, Daphne) |
| Speech-to-text | OpenAI Whisper (open-source model), two backends |
| Database | PostgreSQL (Neon) in production, SQLite locally |
| Frontend | Django templates, vanilla JavaScript (Web Audio API, AudioWorklet, WebSocket) |
| Hosting | Render |

## Speech-to-text backends

Selected with the `STT_BACKEND` environment variable:

- `local` (default): self-hosted [faster-whisper](https://github.com/SYSTRAN/faster-whisper) running on the server CPU.
- `groq`: Whisper large-v3 served by the Groq API. The deployed demo uses this, because the free hosting tier does not have enough CPU and memory to run the model itself.

## How it works

1. The browser captures microphone audio, converts it to 16 kHz mono PCM, and streams chunks over a WebSocket.
2. The server detects pauses and groups speech into phrases.
3. Each phrase is transcribed in a worker thread and the text is sent back to the browser.
4. When the user presses Stop, the session text is saved to the database.

## Run locally

Requires Python 3.12.

```bash
git clone https://github.com/saisreekasturi26/speech-to-text-app.git
cd speech-to-text-app
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux
pip install -r requirements-local.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ (dashboard) and http://127.0.0.1:8000/live/ (live transcription).

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_DEBUG` | `1` enables debug mode | `1` |
| `DJANGO_SECRET_KEY` | Required when debug is off | none |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `127.0.0.1,localhost` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins | empty |
| `DATABASE_URL` | PostgreSQL URL; SQLite when unset | unset |
| `STT_BACKEND` | `local` or `groq` | `local` |
| `WHISPER_MODEL` | Local model size | `small` |
| `GROQ_API_KEY` | Needed for the `groq` backend | unset |

## Known limitations

- Text appears phrase by phrase (after each pause), not word by word.
- Hindi mode expects Hindi speech and English mode expects English speech; use Mix mode for mixed sentences.
- Text-to-speech is not implemented.
- The dashboard has no authentication.
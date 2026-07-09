# Spine AI

Local voice-to-voice assistant with a **multi-LLM brain** — runs entirely on your PC.

## Quick start

1. Install [Ollama](https://ollama.com/download)
2. Pull brains: `ollama pull qwen2.5:7b` and `ollama pull phi3:mini`
3. Double-click **`Launch Spine.bat`**

## Multi-LLM brain (how it works)

Spine routes different tasks to different models:

| Task | Model | Why |
|------|-------|-----|
| Chat / study / research | `qwen2.5:7b` (primary) | Deep thinking |
| PC control / voice planning | `phi3:mini` (fast) | Speed |
| Memory search | `nomic-embed-text` | Knowledge RAG |

### Commands (text mode: `Scripts\run_text.bat`)

```
models list          — installed models + routing map
models routing       — show which brain handles what
models pull phi3:mini
models use fast      — switch chat to fast model
models use primary   — switch chat to smart model
models bench         — speed-test all models
models train spine-custom   — build model from your notes
```

### Voice

- Natural-language commands (not rigid phrases): research, PC control, study, files
- **GPU Whisper (CUDA 12)** via faster-whisper — default `stt_device: cuda` in `spine/config.yaml` (CUDA DLL path helper in `spine/cuda_paths.py`)
- Edge TTS for spoken replies
- Examples: *"Switch to fast model"*, *"Show me research papers on AI"*, *"Play jazz on Spotify"*, *"Open Discord"*

## Features

- **Voice** — configurable listen windows; Whisper `tiny` on GPU when available
- **PC control** — launch apps, Spotify, browser, shell commands, screen click
- **Tray icon** — system tray (right-click Quit)
- **Scheduler** — daily 8am knowledge index (`memory/scheduler.json`)
- **Auto-index** — indexes `memory/knowledge/` on startup
- **Boot** — starts on Windows login via `Install Startup.bat`
- **Stress test** — multi-LLM routing & concurrency: `Scripts\run_stress_test.bat`

## Logs

`logs/spine_YYYYMMDD.log`

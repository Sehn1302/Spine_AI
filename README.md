# Spine AI

A local, multi-agent AI orchestrator that runs on your PC. Spine acts as a formal executive assistant — coordinating specialized agents, retaining conversation memory, and operating entirely offline via [Ollama](https://ollama.com).

Built as a Master's thesis project in Business Management (Data Analytics & AI specialization).

## Features

- **Local-first** — runs on your machine; no cloud API required
- **Formal executive persona** — precise, composed, proactive assistance
- **Persistent memory** — conversations saved to disk and portable across devices
- **Multi-agent ready** — orchestrator architecture prepared for Research, Files, and Study agents
- **Action logging** — every exchange logged for evaluation and thesis analysis

## Requirements

- Windows 10/11
- Python 3.11+
- [Ollama](https://ollama.com/download) with a compatible model (default: `qwen2.5:7b`)
- 16 GB RAM recommended

## Quick Start

### 1. Install dependencies

```powershell
cd D:\Spine_AI
py -3.11 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 2. Pull the language model

```powershell
ollama pull qwen2.5:7b
```

### 3. Run Spine

Double-click `run_spine.bat`, or:

```powershell
.\run_spine.bat
```

## Usage

```
Spine is online. At your service, Sir.

Sir: Good evening, Spine. What can you help me with?

Spine: Good evening, Sir. I am at your disposal...
```

| Command | Action |
|---------|--------|
| `exit` / `quit` / `bye` | End session |
| `new` | Start a fresh conversation |

## Project Structure

```
Spine_AI/
├── spine/
│   ├── main.py           # Text interface entry point
│   ├── orchestrator.py   # Core brain — chat, memory, routing
│   ├── persona.py        # Executive assistant personality
│   └── config.yaml       # Model, paths, user settings
├── agents/               # Specialist agents (Month 3+)
├── memory/
│   └── conversations/    # Saved sessions (portable)
├── logs/                 # Action logs
├── run_spine.bat         # Windows launcher
└── requirements.txt
```

## Configuration

Edit `spine/config.yaml` to change:

- `user.title` — how Spine addresses you (default: `Sir`)
- `spine.model` — Ollama model name
- `paths` — memory and log directories

## Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Text chat + conversation memory | Done |
| 2 | Knowledge base (RAG over your files) | Planned |
| 3 | Multi-agent delegation | Planned |
| 4 | Controlled PC tools | Planned |
| 5 | Voice interface | Planned |

## GPU Note

If you encounter CUDA errors, `run_spine.bat` includes a CPU fallback (`OLLAMA_NUM_GPU=0`). Remove that line after updating your NVIDIA drivers to enable GPU acceleration.

## Author

**Sehan Balajee Pilli** — [github.com/Sehn1302](https://github.com/Sehn1302)

Steinbeis University — Master's in Business Management, Data Analytics & AI

## License

Private thesis project. All rights reserved.

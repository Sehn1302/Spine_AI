# Spine AI

A local, multi-agent AI orchestrator that runs on your PC. Spine acts as a formal executive assistant — coordinating specialized agents, retaining conversation memory, and operating entirely offline via [Ollama](https://ollama.com).

Built as a Master's thesis project in Business Management (Data Analytics & AI specialization).

## Features

- **Local-first** — runs on your machine; no cloud API required
- **Formal executive persona** — precise, composed, proactive assistance
- **Persistent memory** — conversations saved to disk and portable across devices
- **Knowledge base (RAG)** — index your notes and files; Spine recalls them in conversation
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

### 2. Pull the language models

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
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
| `index` | Index files in `memory/knowledge/` |
| `remember <text>` | Save a note to the knowledge base |
| `agents` | List specialist agents |
| `research <query>` | Web search and summary |
| `study <query>` | Thesis and academic guidance |
| `files <path>` | Scan a folder and suggest organization (read-only) |
| `pc <command>` | Controlled PC tools (open, processes, organize) |
| `confirm` / `cancel` | Approve or abort a pending PC file operation |

### Knowledge base

1. Drop `.txt`, `.md`, `.csv`, `.json`, or `.yaml` files into `memory/knowledge/`
2. In Spine, run: `index`
3. Ask questions — Spine automatically searches your files for relevant context

```
Sir: remember My thesis focuses on multi-agent orchestration for local AI systems.

Spine: Noted, Sir. Saved to memory/knowledge/note_20260709_120000.md...

Sir: What is my thesis about?

Spine: Your thesis focuses on multi-agent orchestration for local AI systems, Sir.
```

### Specialist agents

```
Sir: research agentic AI frameworks 2025

Spine: Routing complete, Sir. The Research module reports:
       [summarized web findings with sources]

Sir: study outline my thesis introduction chapter

Spine: Routing complete, Sir. The Study module reports:
       [structured academic guidance]

Sir: files C:\Users\user\Downloads

Spine: Routing complete, Sir. The Files module reports:
       [folder analysis and organization suggestions]
```

### PC tools (Phase 4)

All file changes require your explicit `confirm`. Every action is logged to `logs/actions.jsonl`.

```
Sir: pc processes

Sir: pc open notepad

Sir: pc organize C:\Users\user\Downloads
Spine: Organization plan prepared, Sir.
       PDF/  DOCX/  JPG/ ...
       Type 'confirm' to apply or 'cancel' to abort.

Sir: confirm
Spine: Confirmed, Sir. Moved 12 file(s).
```

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
│   ├── conversations/    # Saved sessions (portable)
│   ├── knowledge/        # Your notes and files (RAG source)
│   └── chroma/           # Vector index (auto-generated)
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
| 2 | Knowledge base (RAG over your files) | Done |
| 3 | Multi-agent delegation | Done |
| 4 | Controlled PC tools | Done |
| 5 | Voice interface (speech in / speech out) | Planned |
| 6 | Visual interface (animated orb UI) | Planned |

### Phase 6 preview — Visual interface (planned)

A desktop visual for Spine — an animated sphere or circle that:

- **Expands and contracts** while Spine is listening, thinking, or speaking
- **Greets you on startup** — e.g. *"Good morning, Sir"* when your PC boots
- **Reacts to your voice** in real time during conversation
- Runs as a **lightweight overlay** or small always-on-top window (local only)

Likely stack: Python + a simple UI framework (e.g. PyQt, Tkinter, or a small web view) wired to Spine's orchestrator state (`idle` → `listening` → `thinking` → `speaking`).

## GPU Note

If you encounter CUDA errors, `run_spine.bat` includes a CPU fallback (`OLLAMA_NUM_GPU=0`). Remove that line after updating your NVIDIA drivers to enable GPU acceleration.

## Author

**Sehan Balajee Pilli** — [github.com/Sehn1302](https://github.com/Sehn1302)

Steinbeis University — Master's in Business Management, Data Analytics & AI

## License

Private thesis project. All rights reserved.

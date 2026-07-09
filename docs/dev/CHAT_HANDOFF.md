# Spine AI — Chat Handoff Document

**Copy everything below this line into a new Cursor chat in the same repo to continue work.**

---

## Project

- **Name:** Spine AI
- **Repo:** https://github.com/Sehn1302/Spine_AI.git
- **Local path:** `D:\Spine_AI`
- **Owner:** Sehan Balajee Pilli (Sir) — Steinbeis University Master's, Business Management + Data Analytics & AI
- **Goal:** Local executive AI orchestrator ("brain") that commands specialist agents ("organs"), for thesis + job portfolio
- **User title:** Sir | **Tone:** Formal executive assistant

## PC Specs

- Ryzen 7 4800H, 16 GB RAM, RTX 3050 4 GB
- Ollama models: `qwen2.5:7b` (chat), `nomic-embed-text` (embeddings)
- GPU working after driver update; removed `OLLAMA_NO_GPU=1` from Windows env

## How to Run

| Launcher | Purpose |
|----------|---------|
| `run_spine.bat` | Text mode |
| `run_spine_voice.bat` | Voice mode |
| `run_spine_visual.bat` | Animated orb + voice |

```powershell
cd D:\Spine_AI
.\.venv\Scripts\pip install -r requirements.txt
```

## Phases Completed

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Text chat + conversation memory | Done |
| 2 | Knowledge base (RAG) — `index`, `remember` | Done |
| 3 | Multi-agent — research, study, files, pc | Done |
| 4 | Controlled PC tools + confirm/cancel + action log | Done |
| 5 | Voice — Whisper STT + Edge TTS | Done |
| 6 | Visual orb UI (idle/listening/thinking/speaking) | Done |

## Key Commands

```
voice / visual / devices / agents
index / remember <text>
research <query> / study <query> / files <path>
pc open <app> / pc processes / pc organize <folder>
confirm / cancel
```

## Voice Greeting (spoken on voice/visual start)

Time-based:
- **"Good morning, Sir. I am online. How may I assist you?"**
- **"Good afternoon, Sir. I am online. How may I assist you?"**
- **"Good evening, Sir. I am online. How may I assist you?"**

## Audio / Bluetooth

- Uses **Windows default microphone** unless set in `spine/config.yaml`
- Type `devices` to list all mics/speakers with index numbers
- Set `input_device: 2` (index) or `input_device: "Galaxy Buds"` (name match) in config
- For Bluetooth: set earbuds as default Input + Output in Windows Sound settings
- Use **Hands-Free** profile for mic on Bluetooth earbuds

## Architecture — How Spine Acts as the "Brain"

Spine is **not one AI** — it is an **orchestrator** over multiple components:

```
Sir (you)
    ↓
SPINE ORCHESTRATOR (brain)
    ├── Memory: conversations (JSON) + knowledge base (ChromaDB RAG)
    ├── Persona: formal executive system prompt
    ├── Router: parses commands → delegates to agents
    └── Ollama LLM (qwen2.5:7b): reasoning + synthesis
            ↓
    SPECIALIST AGENTS (organs)
    ├── Research Agent → web search (DuckDuckGo) + LLM summary
    ├── Study Agent → thesis help + pulls from your knowledge base
    ├── Files Agent → read-only folder analysis
    └── PC Agent → open apps, processes, organize (with confirm)
```

### "Training" — what it actually means in this project

Spine does **not** retrain neural networks from scratch. Instead:

1. **Knowledge ingestion** — `remember` and `index` add your notes/files to vector memory (RAG). Agents and Spine **learn your context** without model fine-tuning.
2. **Delegation** — Brain routes tasks to the right specialist; each agent has its own system prompt and tools.
3. **Persistent memory** — Conversations and knowledge survive sessions; copy `memory/` folder to transfer.
4. **Action logs** — `logs/actions.jsonl` records what PC agent did (thesis evaluation data).
5. **Future self-improvement** — Thesis "future work": fine-tuning, feedback loops, agent performance metrics.

**Thesis framing:** *"A local multi-agent orchestration architecture where a central executive AI coordinates specialist modules with shared persistent memory."*

## File Structure

```
D:\Spine_AI\
├── spine/
│   ├── main.py, orchestrator.py, persona.py, router.py
│   ├── knowledge.py, voice.py, voice_mode.py, visual_mode.py
│   ├── orb.py, greeting.py, action_log.py, config.yaml
├── agents/ — research, study, files, pc, base
├── memory/ — conversations, knowledge, chroma
├── logs/ — spine logs + actions.jsonl
├── run_spine.bat, run_spine_voice.bat, run_spine_visual.bat
└── requirements.txt
```

## Git / Tooling Notes

- Portable Git: `%LOCALAPPDATA%\Programs\MinGit\cmd\git.exe`
- Python 3.11 venv at `D:\Spine_AI\.venv`
- `.vscode/settings.json` points Cursor to MinGit

## Conversation History Summary

1. User wanted JARVIS-like local AI orchestrator for thesis (7 months timeline)
2. Built Phase 1 text Spine — formal, calls user Sir
3. GitHub repo: Sehn1302/Spine_AI — removed all "JARVIS" references from code/history
4. Phase 2 RAG knowledge base
5. Phase 3 multi-agent delegation
6. Phase 4 PC tools with confirmation
7. Fixed GPU — `OLLAMA_NO_GPU=1` was blocking CUDA
8. Phase 5 voice interface
9. Phase 6 visual orb + time-based voice greeting
10. User wants Bluetooth mic support — `devices` command + config `input_device`
11. Visual orb expands/contracts by state (listening/thinking/speaking)

## Likely Next Steps

- Startup on Windows boot (Task Scheduler)
- PDF ingestion for knowledge base
- Agent performance metrics for thesis evaluation
- Bluetooth output device selection (if needed beyond Windows default)
- Polish orb UI (3D sphere, transparency)

## Prompt to Continue in New Chat

```
Continue Spine AI at D:\Spine_AI. Read CHAT_HANDOFF.md and README.md.
All phases 1-6 are done. Help me with [your next task].
User is Sir. Formal tone. Push changes to github.com/Sehn1302/Spine_AI.
```

---

*End of handoff — paste into new chat as needed.*

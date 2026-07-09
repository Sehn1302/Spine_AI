# Spine AI

Your personal AI assistant — installs like a game, runs entirely on your PC.

## Quick Start (3 steps)

1. **Install [Ollama](https://ollama.com/download)** (Spine's brain)
2. **Double-click `Install Spine.bat`** — downloads everything and configures automatically
3. **Double-click `Launch Spine.bat`** — say **"Spine, wake up"** to start

That's it.

## What you get

- **Personal assistant** — voice + small orb, formal and hands-free
- **Remembers you** — conversations and knowledge saved locally
- **Multi-agent brain** — research, study, files, PC control
- **LLM supervision** — install and switch small local models (`models list`, `models pull`, `models use`)
- **Adapts to your PC** — auto-detects Bluetooth headsets, noise cancellation, installed software

## Folder layout

```
Spine_AI/
├── Install Spine.bat      ← run once
├── Launch Spine.bat       ← your daily launcher
├── spine/                 ← application code
├── agents/                ← specialist modules
├── scripts/               ← internal launchers
├── installer/             ← setup wizard
├── memory/                ← your data (conversations, knowledge)
└── logs/                  ← runtime logs
```

## Voice commands

| Say | Action |
|-----|--------|
| "Spine, wake up" | Activate assistant |
| "Spine, sleep" | Go silent |
| Natural speech | Ask anything after wake |

## Text commands

| Command | Action |
|---------|--------|
| `models list` | Show installed LLMs |
| `models pull phi3:mini` | Download a small model |
| `models use qwen2.5:7b` | Switch active model |
| `models recommend` | Hardware-based suggestions |
| `index` | Index files in `memory/knowledge/` |
| `remember <text>` | Save a note |
| `research / study / files / pc` | Delegate to agents |
| `capabilities` | Show detected PC software |

## Requirements

- Windows 10/11
- Python 3.11+ (installer checks)
- Ollama
- 8 GB RAM minimum (16 GB recommended for 7B models)

## Thesis

Built by Sehan Balajee Pilli — Steinbeis University Master's in Business Management (Data Analytics & AI).

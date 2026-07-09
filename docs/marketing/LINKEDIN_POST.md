# LinkedIn / Social Post — Spine AI

**Use the section below as your main LinkedIn post.** Adjust tone once if needed; hashtags are at the bottom.

---

## Main post (LinkedIn)

Most “AI assistants” are someone else’s cloud, someone else’s model, and someone else’s privacy policy.

I wanted the opposite: an **executive-grade assistant that runs 100% on my laptop** — no API keys, no data leaving the machine, no single generic model pretending to be good at everything.

So I built **Spine AI** — a local **multi-LLM orchestrator** with specialist agents, voice-to-voice, RAG, and natural-language PC control. It is my **Master’s portfolio / thesis project** (Steinbeis University — Business Management + Data Analytics & AI), and it is deliberately **not** ChatGPT-in-a-tab, Alexa, or Copilot.

**What is wrong with the default cloud-AI experience?**
- Your prompts, files, and voice live on third-party servers
- One model for chat, coding, search, and automation — slow *or* shallow, rarely both
- No real **orchestration**: no “brain” that delegates to specialists on *your* machine
- PC automation is an afterthought, not a first-class citizen

**What Spine AI does differently**
- **Fully local** on consumer hardware (Ryzen 7 + RTX 3050) via **Ollama** — cloud-optional, privacy-first
- **Multi-LLM brain**: task-aware routing — **qwen2.5:7b** for deep chat / research / study; **phi3:mini** for fast PC planning and voice latency — not one model for every job
- **Orchestrator + specialist agents** (research, study, files, PC) — a “brain + organs” architecture, not a monolithic chatbot
- **Voice-to-voice**: **GPU Whisper** (CUDA 12, faster-whisper) + **Edge TTS** — natural language in and out
- **Natural-language PC control**: “write this down” → Notepad, organise files, Spotify, open apps, research workflows
- **RAG knowledge base** with **auto-index** on startup and scheduled indexing
- **Production-minded UX**: system tray, boot startup, scheduler — built to stay on, not demo once
- **Formal executive assistant persona** — consistent, professional responses for daily use
- **Stress-tested** multi-model concurrent routing (see metrics below)

**Tech stack (what I applied in practice)**
- Python, multi-agent orchestration, RAG (Chroma + embeddings)
- Ollama (qwen2.5:7b, phi3:mini, nomic-embed-text)
- faster-whisper on CUDA, Edge TTS, Windows automation
- Router / model manager, action planner, host capability scanning

**Results / benchmarks (local, warm runs)**
| Area | Result |
|------|--------|
| Fast path (phi3:mini) | ~**0.8s** response (warm) |
| Deep path (qwen2.5:7b) | ~**2.1s** response (warm) |
| Whisper STT | ~**0.5s** on **GPU (CUDA)** vs ~**2s** on CPU |
| Multi-LLM stress test | **11/11** checks passed (routing, agents, concurrency) |

Re-run benchmarks: `Scripts\run_stress_test.bat` and `models bench` in text mode.

**Repository:** https://github.com/Sehn1302/Spine_AI

If you are hiring for **AI engineering**, **data & analytics**, **voice/edge AI**, or **automation** — I am open to conversations. This project is proof I can ship an end-to-end system, not just prompt a API.

What would *you* want a local orchestrator to handle first — voice, files, or research?

---

## Hashtags (paste after the post body)

#AI #ArtificialIntelligence #LLM #GenAI #GenerativeAI #MachineLearning #DeepLearning #NLP #RAG #RetrievalAugmentedGeneration #MultiAgent #MultiAgentSystems #VoiceAI #LocalAI #EdgeAI #OnDeviceAI #Python #Ollama #Whisper #CUDA #MLOps #AIEngineering #DataAnalytics #BusinessAnalytics #Automation #IntelligentAutomation #PortfolioProject #Thesis #Steinbeis #Innovation #DigitalTransformation #ProductManagement #OpenToWork #Hiring #TechJobs #Recruitment #SoftwareEngineering #Windows #OpenSource #PersonalProject #ExecutiveAssistant #Privacy #ResponsibleAI

---

## Twitter / X (≤280 characters)

Built Spine AI: 100% local multi-LLM orchestrator (qwen + phi3), RAG, GPU Whisper voice, PC control—NOT cloud ChatGPT. 11/11 stress tests. Master's portfolio. https://github.com/Sehn1302/Spine_AI #LocalAI #LLM #RAG #Python #OpenToWork

*(Character count: ~248 — room for a tweak.)*

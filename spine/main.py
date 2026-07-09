"""Spine — text interface entry point."""

from __future__ import annotations

import sys

from orchestrator import SpineOrchestrator, load_config
from router import list_agents
from voice import VoiceInterface
from voice_mode import run_voice_mode


BANNER = """
================================================================
   S P I N E
   Executive AI Orchestrator — Local Interface
================================================================
  Commands:
    exit, quit, bye      — End session
    new                  — Start a fresh conversation
    index                — Index files in memory/knowledge/
    remember <text>      — Save a note to the knowledge base
    agents               — List specialist agents
    research <query>     — Web search and summary
    study <query>        — Thesis and academic guidance
    files <path>         — Scan a folder (read-only)
    pc <command>         — Controlled PC tools
    confirm / cancel     — Approve or abort pending PC actions
    voice                — Enter voice mode (speech in / speech out)
================================================================
"""


def main() -> None:
    voice_startup = "--voice" in sys.argv
    print(BANNER)

    try:
        spine = SpineOrchestrator()
    except Exception as exc:
        print(f"Failed to initialize Spine: {exc}")
        sys.exit(1)

    title = spine.user_title
    config = load_config()
    voice_cfg = config.get("voice", {})

    voice = VoiceInterface(
        stt_model=voice_cfg.get("stt_model", "base"),
        stt_device=voice_cfg.get("stt_device", "cuda"),
        tts_voice=voice_cfg.get("tts_voice", "en-GB-RyanNeural"),
        record_seconds=voice_cfg.get("record_seconds", 5),
        sample_rate=voice_cfg.get("sample_rate", 16000),
    )

    if voice_startup:
        run_voice_mode(spine, voice)
        return

    print(f"Spine is online. At your service, {title}.\n")

    while True:
        try:
            user_input = input(f"{title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\nShutting down. Good evening, {title}.")
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in {"exit", "quit", "bye", "goodbye"}:
            print(f"\nSpine: Very good, {title}. I shall remain available when you return.")
            break

        if lowered == "new":
            spine.new_session()
            print(f"\nSpine: A fresh session has been initiated, {title}.\n")
            continue

        if lowered == "index":
            print("\nSpine: ", end="", flush=True)
            print(spine.index_knowledge())
            print()
            continue

        if lowered.startswith("remember "):
            note = user_input[len("remember ") :].strip()
            print("\nSpine: ", end="", flush=True)
            print(spine.remember(note))
            print()
            continue

        if lowered == "agents":
            print(f"\nSpine:\n{list_agents()}\n")
            continue

        if lowered == "voice":
            run_voice_mode(spine, voice)
            print(f"Spine is online. At your service, {title}.\n")
            continue

        print("\nSpine: ", end="", flush=True)
        reply = spine.handle(user_input)
        print(reply)
        print()


if __name__ == "__main__":
    main()

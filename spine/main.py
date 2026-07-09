"""Spine — text interface entry point."""

from __future__ import annotations

import sys

from greeting import time_farewell, time_greeting
from boot import ensure_single_instance, release_instance_lock, setup_boot_logging
from orchestrator import SpineOrchestrator, load_config
from orb import VisualOrb
from router import list_agents
from voice import VoiceInterface, list_audio_devices
from voice_mode import run_voice_mode
from visual_mode import run_visual_mode


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
    visual               — Animated orb + voice mode
    devices              — List microphones and speakers
    capabilities         — Show software detected on this PC
    refresh audio        — Re-scan for newly connected wireless devices
    models list / pull / use — Manage local LLMs under Spine
================================================================
"""


def main() -> None:
    voice_startup = "--voice" in sys.argv
    visual_startup = "--visual" in sys.argv
    boot_startup = "--startup" in sys.argv

    if not boot_startup:
        print(BANNER)

    if boot_startup:
        config = load_config()
        setup_boot_logging(config["paths"]["logs"])
        if not ensure_single_instance():
            sys.exit(0)

    try:
        spine = SpineOrchestrator(quiet=boot_startup)
    except Exception as exc:
        if boot_startup:
            import logging
            logging.exception("Failed to initialize Spine: %s", exc)
        else:
            print(f"Failed to initialize Spine: {exc}")
        release_instance_lock()
        sys.exit(1)

    title = spine.user_title
    if not boot_startup:
        config = load_config()
    else:
        config = spine.config
    voice_cfg = config.get("voice", {})
    visual_cfg = config.get("visual", {})
    wake_cfg = config.get("wake", {})

    wake_phrases = tuple(wake_cfg.get("phrases", ["spine wake up", "spine wakeup", "spine, wake up"]))

    voice = VoiceInterface(
        stt_model=voice_cfg.get("stt_model", "base"),
        stt_device=voice_cfg.get("stt_device", "cuda"),
        tts_voice=voice_cfg.get("tts_voice", "en-GB-RyanNeural"),
        record_seconds=voice_cfg.get("record_seconds", 6),
        sample_rate=voice_cfg.get("sample_rate", 16000),
        input_device=voice_cfg.get("input_device", "default"),
        output_device=voice_cfg.get("output_device", "default"),
        sleep_listen_seconds=wake_cfg.get("sleep_listen_seconds", 3),
        min_peak=voice_cfg.get("min_peak", 0.004),
        passive_min_peak=voice_cfg.get("passive_min_peak", 0.008),
        auto_bluetooth=voice_cfg.get("auto_bluetooth", True),
        prefer_enhanced_audio=voice_cfg.get("prefer_enhanced_audio", True),
        noise_cancellation=voice_cfg.get("noise_cancellation", True),
        listen_mode=voice_cfg.get("listen_mode", "continuous"),
        silence_stop_seconds=voice_cfg.get("silence_stop_seconds", 1.0),
        max_utterance_seconds=voice_cfg.get("max_utterance_seconds", 25.0),
        conversation_min_peak=voice_cfg.get("conversation_min_peak", 0.003),
        boot_use_default_mic=voice_cfg.get("boot_use_default_mic", True),
    )

    wake_kwargs = {
        "start_awake": not wake_cfg.get("start_asleep", False),
        "sleep_timeout": wake_cfg.get("sleep_timeout_seconds", 90),
        "conversational": voice_cfg.get("conversational", True),
        "wake_phrases": wake_phrases,
    }

    orb = VisualOrb(
        size=visual_cfg.get("orb_size", 48),
        always_on_top=visual_cfg.get("always_on_top", True),
        position=visual_cfg.get("position", "top-left"),
    )

    if visual_startup:
        wake_kwargs["start_awake"] = False
        try:
            run_visual_mode(spine, voice, orb, wake_kwargs=wake_kwargs, boot_mode=boot_startup)
        finally:
            release_instance_lock()
        return

    if voice_startup:
        run_voice_mode(spine, voice, **wake_kwargs)
        return

    print(f"Spine: {time_greeting(title)}\n")

    while True:
        try:
            user_input = input(f"{title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\nShutting down. {time_farewell(title)}")
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in {"exit", "quit", "bye", "goodbye"}:
            print(f"\nSpine: {time_farewell(title)}")
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

        if lowered == "devices":
            print(f"\n{list_audio_devices()}\n")
            continue

        if lowered in {"refresh audio", "refresh"}:
            voice.refresh_devices()
            continue

        if lowered in {"capabilities", "host", "refresh capabilities"}:
            if lowered == "refresh capabilities":
                spine.host_caps.refresh()
            print(f"\n{spine.host_caps.format_report()}\n")
            continue

        if lowered == "voice":
            run_voice_mode(spine, voice, **wake_kwargs)
            print(f"Spine: {time_greeting(title)}\n")
            continue

        if lowered == "visual":
            run_visual_mode(spine, voice, orb, wake_kwargs=wake_kwargs)
            print(f"Spine: {time_greeting(title)}\n")
            continue

        print("\nSpine: ", end="", flush=True)
        reply = spine.handle(user_input)
        print(reply)
        print()


if __name__ == "__main__":
    main()

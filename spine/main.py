"""Spine — local voice assistant + multi-LLM brain."""

from __future__ import annotations

import sys

from orchestrator import SpineOrchestrator
from orb import VisualOrb
from voice import VoiceInterface
from voice_mode import run_voice_session
from visual_mode import run_visual_mode


def main() -> None:
    visual_mode = "--visual" in sys.argv
    voice_mode = "--voice" in sys.argv
    text_mode = "--text" in sys.argv

    if not visual_mode and not voice_mode and not text_mode:
        visual_mode = True

    spine = SpineOrchestrator()
    config = spine.config
    voice_cfg = config.get("voice", {})
    visual_cfg = config.get("visual", {})

    voice = VoiceInterface(
        stt_model=voice_cfg.get("stt_model", "base"),
        stt_device=voice_cfg.get("stt_device", "cuda"),
        tts_voice=voice_cfg.get("tts_voice", "en-GB-RyanNeural"),
        record_seconds=voice_cfg.get("record_seconds", 7),
        sample_rate=voice_cfg.get("sample_rate", 16000),
        min_peak=voice_cfg.get("min_peak", 0.0008),
        listen_mode=voice_cfg.get("listen_mode", "fixed"),
        noise_cancellation=False,
        auto_bluetooth=False,
    )

    if visual_mode:
        orb = VisualOrb(
            size=visual_cfg.get("orb_size", 48),
            always_on_top=visual_cfg.get("always_on_top", True),
            position=visual_cfg.get("position", "top-left"),
        )
        run_visual_mode(spine, voice, orb)
        return

    if voice_mode:
        run_voice_session(spine, voice)
        return

    print("\n=== SPINE TEXT ===")
    print("Commands: models list | models pull <name> | models use <name>")
    print("          research / study / files / pc  |  exit\n")
    title = spine.user_title

    while True:
        try:
            user_input = input(f"{title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "bye"}:
            break
        print("Spine:", spine.handle(user_input))


if __name__ == "__main__":
    main()

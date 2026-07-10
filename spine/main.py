"""Spine — local voice assistant + multi-LLM brain."""

from __future__ import annotations

import sys

from boot import preload_voice, register_shutdown_hook, release_instance_lock, run_boot_sequence
from orchestrator import SpineOrchestrator, load_config
from orb import VisualOrb
from voice import VoiceInterface
from voice_mode import run_voice_session
from visual_mode import run_visual_mode


def main() -> None:
    login_boot = "--boot" in sys.argv
    visual_mode = "--visual" in sys.argv
    voice_mode = "--voice" in sys.argv
    text_mode = "--text" in sys.argv

    if not visual_mode and not voice_mode and not text_mode:
        visual_mode = True

    config = load_config()
    needs_voice = visual_mode or voice_mode

    if not run_boot_sequence(config, login_boot=login_boot, needs_voice=False):
        sys.exit(0)

    spine = SpineOrchestrator(config=config, quiet=login_boot)
    voice_cfg = config.get("voice", {})
    visual_cfg = config.get("visual", {})

    voice = VoiceInterface(
        stt_model=voice_cfg.get("stt_model", "tiny"),
        stt_device=voice_cfg.get("stt_device", "cuda"),
        tts_voice=voice_cfg.get("tts_voice", "en-GB-RyanNeural"),
        record_seconds=voice_cfg.get("record_seconds", 7),
        sample_rate=voice_cfg.get("sample_rate", 16000),
        min_peak=voice_cfg.get("min_peak", 0.0008),
        listen_mode=voice_cfg.get("listen_mode", "fixed"),
        noise_cancellation=False,
        auto_bluetooth=False,
    )

    if needs_voice and config.get("boot", {}).get("preload_whisper", True):
        preload_voice(voice)

    register_shutdown_hook()

    try:
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
    finally:
        release_instance_lock()


if __name__ == "__main__":
    main()

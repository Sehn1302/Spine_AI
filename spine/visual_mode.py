"""Visual mode — animated orb wired to voice session."""

from __future__ import annotations

import logging
import threading
import time

from boot import log_boot, preload_voice, wait_for_audio, wait_for_ollama
from orchestrator import SpineOrchestrator
from orb import VisualOrb
from voice import SpineState, VoiceInterface
from voice_mode import run_voice_mode


def run_visual_mode(
    spine: SpineOrchestrator,
    voice: VoiceInterface,
    orb: VisualOrb,
    *,
    wake_kwargs: dict | None = None,
    boot_mode: bool = False,
) -> None:
    options = {"skip_greeting": True, "start_awake": False, **(wake_kwargs or {})}

    def on_state_change(state: SpineState) -> None:
        orb.set_state(state)

    voice.on_state_change = on_state_change

    def voice_thread() -> None:
        try:
            orb.set_state(SpineState.SLEEPING)
            if boot_mode:
                log_boot("Boot voice thread started.")
                wait_for_audio(8.0)
                if not wait_for_ollama(90):
                    log_boot("Ollama unavailable — voice answers will fail until Ollama starts.")
                voice.refresh_devices()
                if not preload_voice(voice):
                    log_boot("Whisper failed — trying CPU fallback.")
                    voice.stt_device = "cpu"
                    voice._whisper = None
                    preload_voice(voice)
                log_boot("Voice subsystem ready. Say 'Spine wake up'.")
                try:
                    voice.speak("Spine is online. Say Spine wake up when you need me.")
                except Exception as exc:
                    log_boot(f"Startup speak skipped: {exc}")

            run_voice_mode(spine, voice, **options)
        except Exception as exc:
            logging.exception("Voice thread crashed: %s", exc)
        finally:
            orb.stop()

    thread = threading.Thread(target=voice_thread, daemon=True)
    thread.start()
    orb.run()

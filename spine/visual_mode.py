"""Visual mode — orb + voice + system tray."""

from __future__ import annotations

import logging
import sys
import threading

from boot import release_instance_lock
from orchestrator import SpineOrchestrator
from orb import VisualOrb
from tray import run_tray
from voice import SpineState, VoiceInterface
from voice_mode import run_voice_session


def run_visual_mode(spine: SpineOrchestrator, voice: VoiceInterface, orb: VisualOrb) -> None:
    voice.on_state_change = lambda s: orb.set_state(s)
    stop_event = threading.Event()

    def voice_thread() -> None:
        try:
            orb.set_state(SpineState.LISTENING)
            voice.speak("Spine is ready. Speak when you hear the listening tone.")
            run_voice_session(spine, voice)
        except Exception as exc:
            logging.exception("Voice thread failed: %s", exc)
        finally:
            stop_event.set()
            orb.stop()

    threading.Thread(target=voice_thread, daemon=True).start()

    visual_cfg = spine.config.get("visual", {})
    if visual_cfg.get("tray_icon", True):
        run_tray(
            on_quit=lambda: (stop_event.set(), orb.stop(), release_instance_lock(), sys.exit(0)),
            title="Spine AI",
        )

    orb.run()

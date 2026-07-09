"""Visual mode — animated orb wired to voice session."""

from __future__ import annotations

import threading

from greeting import voice_greeting
from orchestrator import SpineOrchestrator
from orb import VisualOrb
from voice import SpineState, VoiceInterface
from voice_mode import run_voice_mode


def run_visual_mode(spine: SpineOrchestrator, voice: VoiceInterface, orb: VisualOrb) -> None:
    title = spine.user_title

    def on_state_change(state: SpineState) -> None:
        orb.set_state(state)

    voice.on_state_change = on_state_change

    def voice_thread() -> None:
        greeting = voice_greeting(title)
        print(f"Spine: {greeting}\n")
        orb.set_state(SpineState.SPEAKING)
        voice.speak(greeting)
        orb.set_state(SpineState.IDLE)
        run_voice_mode(spine, voice, skip_greeting=True)
        orb.stop()

    thread = threading.Thread(target=voice_thread, daemon=True)
    thread.start()
    orb.run()

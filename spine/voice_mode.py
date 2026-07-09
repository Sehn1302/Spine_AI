"""Voice session — listen, think, speak loop."""

from __future__ import annotations

import logging

from orchestrator import SpineOrchestrator
from voice import VoiceInterface


def run_voice_session(spine: SpineOrchestrator, voice: VoiceInterface) -> None:
    title = spine.user_title
    print("\n=== SPINE VOICE ===")
    print("Speak after you hear the chime. Say 'exit' to quit.\n")

    while True:
        try:
            spoken = voice.listen()
        except ValueError as exc:
            logging.info("Listen: %s", exc)
            continue
        except Exception as exc:
            print(f"Voice error: {exc}")
            continue

        if spoken.lower().strip() in {"exit", "quit", "bye", "goodbye"}:
            print("Goodbye.")
            break

        voice.thinking()
        print(f"\n{title}: {spoken}")
        print("Spine: ", end="", flush=True)
        reply = spine.handle(spoken)
        print(reply)
        voice.speak(reply)

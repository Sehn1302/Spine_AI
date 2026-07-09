"""Voice mode session loop."""

from __future__ import annotations

from greeting import time_farewell, voice_greeting
from orchestrator import SpineOrchestrator
from voice import VoiceInterface


def run_voice_mode(
    spine: SpineOrchestrator,
    voice: VoiceInterface,
    *,
    skip_greeting: bool = False,
) -> None:
    title = spine.user_title
    print("\n================================================================")
    print("   VOICE MODE — Press Enter to speak, type 'text' to switch")
    print("================================================================\n")

    if not skip_greeting:
        greeting = voice_greeting(title)
        print(f"Spine: {greeting}\n")
        voice.speak(greeting)

    while True:
        try:
            control = input(f"[Enter]=speak | {title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\nVoice mode ended. {time_farewell(title)}")
            break

        if control.lower() in {"text", "exit", "quit", "bye"}:
            print(f"\nSpine: Returning to text mode, {title}.\n")
            break

        if control:
            reply = spine.handle(control)
            print(f"\nSpine: {reply}\n")
            voice.speak(reply)
            continue

        try:
            spoken = voice.listen()
        except ValueError as exc:
            print(f"\nSpine: {exc}\n")
            continue
        except Exception as exc:
            print(f"\nSpine: Voice capture failed — {exc}\n")
            continue

        voice.thinking()
        print("\nSpine: ", end="", flush=True)
        reply = spine.handle(spoken)
        print(reply)
        print()
        voice.speak(reply)

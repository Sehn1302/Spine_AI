"""Voice mode session loop."""

from __future__ import annotations

from datetime import datetime

from orchestrator import SpineOrchestrator
from voice import VoiceInterface


def time_greeting(title: str) -> str:
    hour = datetime.now().hour
    if hour < 12:
        period = "Good morning"
    elif hour < 17:
        period = "Good afternoon"
    else:
        period = "Good evening"
    return f"{period}, {title}. Spine is online and listening."


def run_voice_mode(spine: SpineOrchestrator, voice: VoiceInterface) -> None:
    title = spine.user_title
    print("\n================================================================")
    print("   VOICE MODE — Press Enter to speak, type 'text' to switch")
    print("================================================================\n")

    greeting = time_greeting(title)
    print(f"Spine: {greeting}\n")
    voice.speak(greeting)

    while True:
        try:
            control = input(f"[Enter]=speak | {title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\nVoice mode ended. Good evening, {title}.")
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

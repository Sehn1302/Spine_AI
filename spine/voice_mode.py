"""Voice mode with sleep/wake — silent until 'Spine, wake up'."""

from __future__ import annotations

import msvcrt
import time

from greeting import time_farewell, voice_greeting
from orchestrator import SpineOrchestrator
from voice import VoiceInterface
from wake import is_sleep_phrase, is_wake_phrase, sleep_response, wake_response


def _enter_sleep(voice: VoiceInterface, title: str, *, speak: bool = False) -> None:
    voice.sleeping()
    print(f"\nSpine: Sleeping. Say 'Spine, wake up' or press Enter.\n")
    if speak:
        voice.speak(sleep_response(title))


def _wait_for_wake(voice: VoiceInterface, title: str) -> bool:
    """Listen for wake phrase or Enter key. Returns True when woken."""
    voice.sleeping()

    while True:
        if msvcrt.kbhit():
            msvcrt.getch()
            print(f"\nSpine: {wake_response(title)}\n")
            voice.speak(wake_response(title))
            return True

        text = voice.listen_passive()
        if text:
            print(f'Heard: "{text}"')
            if is_wake_phrase(text):
                print(f"\nSpine: {wake_response(title)}\n")
                voice.speak(wake_response(title))
                return True

        time.sleep(0.1)


def run_voice_mode(
    spine: SpineOrchestrator,
    voice: VoiceInterface,
    *,
    skip_greeting: bool = False,
    start_awake: bool = False,
    sleep_timeout: int = 90,
) -> None:
    title = spine.user_title
    awake = start_awake
    last_active = time.time()

    print("\n================================================================")
    print("   VOICE MODE")
    print("   Awake: speak normally | Sleep: 'Spine, sleep' or idle timeout")
    print("   Wake:  'Spine, wake up' or press Enter while sleeping")
    print("================================================================\n")

    if not skip_greeting and awake:
        greeting = voice_greeting(title)
        print(f"Spine: {greeting}\n")
        voice.speak(greeting)
        last_active = time.time()
    elif not awake:
        _enter_sleep(voice, title)

    while True:
        if not awake:
            if not _wait_for_wake(voice, title):
                continue
            awake = True
            last_active = time.time()
            continue

        try:
            control = input(f"[Enter]=speak | sleep | {title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\nVoice mode ended. {time_farewell(title)}")
            break

        if control.lower() in {"text", "exit", "quit", "bye"}:
            print(f"\nSpine: Returning to text mode, {title}.\n")
            break

        if control.lower() in {"sleep", "silent", "standby"}:
            awake = False
            _enter_sleep(voice, title, speak=True)
            continue

        if control:
            last_active = time.time()
            reply = spine.handle(control)
            print(f"\nSpine: {reply}\n")
            voice.speak(reply)
            continue

        if time.time() - last_active > sleep_timeout:
            awake = False
            _enter_sleep(voice, title, speak=False)
            continue

        try:
            spoken = voice.listen()
            last_active = time.time()
        except ValueError as exc:
            print(f"\nSpine: {exc}\n")
            continue
        except Exception as exc:
            print(f"\nSpine: Voice capture failed — {exc}\n")
            continue

        if is_sleep_phrase(spoken):
            awake = False
            _enter_sleep(voice, title, speak=True)
            continue

        voice.thinking()
        print("\nSpine: ", end="", flush=True)
        reply = spine.handle(spoken)
        print(reply)
        print()
        voice.speak(reply)
        last_active = time.time()

        if time.time() - last_active > sleep_timeout:
            awake = False
            _enter_sleep(voice, title, speak=False)

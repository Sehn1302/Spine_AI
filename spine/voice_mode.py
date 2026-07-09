"""Voice mode with sleep/wake and hands-free conversation loop."""

from __future__ import annotations

import msvcrt
import time

from greeting import time_farewell, voice_greeting
from orchestrator import SpineOrchestrator
from voice import VoiceInterface
from wake import is_sleep_phrase, is_wake_phrase, sleep_response, wake_response


def _enter_sleep(voice: VoiceInterface, title: str, *, speak: bool = False) -> None:
    voice.sleeping()
    print(f"\nSpine: Sleeping. Say 'Spine, wake up'.\n")
    if speak:
        voice.speak(sleep_response(title))


def _wait_for_wake(voice: VoiceInterface, title: str, wake_phrases: tuple[str, ...]) -> bool:
    """Listen silently — only 'Spine wake up' activates Spine."""
    voice.sleeping()
    while True:
        text = voice.listen_passive()
        if text and is_wake_phrase(text, wake_phrases):
            print(f'Wake phrase detected: "{text}"')
            voice.speak(wake_response(title))
            return True
        time.sleep(0.05)


def _conversation_loop(
    spine: SpineOrchestrator,
    voice: VoiceInterface,
    title: str,
    sleep_timeout: int,
) -> bool:
    """Hands-free listen → think → speak loop. Returns False to exit voice mode."""
    last_active = time.time()

    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            if key == "q":
                return False
            if key == "s":
                _enter_sleep(voice, title, speak=True)
                return True

        if time.time() - last_active > sleep_timeout:
            _enter_sleep(voice, title, speak=False)
            return True

        try:
            spoken = voice.listen()
            last_active = time.time()
        except ValueError:
            continue
        except Exception as exc:
            print(f"\nSpine: Voice error — {exc}\n")
            continue

        if spoken.lower() in {"exit", "quit", "bye", "goodbye"}:
            return False

        if is_sleep_phrase(spoken):
            _enter_sleep(voice, title, speak=True)
            return True

        voice.thinking()
        print(f"\nSir: {spoken}")
        print("Spine: ", end="", flush=True)
        reply = spine.handle(spoken)
        print(reply)
        voice.speak(reply)
        last_active = time.time()


def run_voice_mode(
    spine: SpineOrchestrator,
    voice: VoiceInterface,
    *,
    skip_greeting: bool = False,
    start_awake: bool = False,
    sleep_timeout: int = 90,
    conversational: bool = True,
    wake_phrases: tuple[str, ...] | None = None,
) -> None:
    title = spine.user_title
    awake = start_awake
    phrases = wake_phrases or ("spine wake up", "spine wakeup", "spine, wake up")

    print("\n================================================================")
    print("   VOICE MODE — sleeping until wake phrase")
    print("   Say 'Spine, wake up' to activate")
    print("   Say 'Spine, sleep' to go silent | 'exit' to quit")
    print("================================================================\n")

    if not skip_greeting and awake:
        greeting = voice_greeting(title)
        print(f"Spine: {greeting}\n")
        voice.speak(greeting)
    elif not awake:
        _enter_sleep(voice, title)

    while True:
        if not awake:
            if not _wait_for_wake(voice, title, phrases):
                continue
            awake = True
            if conversational:
                greeting = voice_greeting(title)
                voice.speak(greeting)

        if conversational:
            awake = _conversation_loop(spine, voice, title, sleep_timeout)
            if not awake:
                print(f"\n{time_farewell(title)}")
                break
            continue

        try:
            control = input(f"[Enter]=speak | sleep | {title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{time_farewell(title)}")
            break

        if control.lower() in {"text", "exit", "quit", "bye"}:
            break
        if control.lower() in {"sleep", "silent"}:
            awake = False
            _enter_sleep(voice, title, speak=True)
            continue
        if control:
            reply = spine.handle(control)
            voice.speak(reply)
            continue

        try:
            spoken = voice.listen()
        except ValueError as exc:
            print(f"Spine: {exc}")
            continue

        if is_sleep_phrase(spoken):
            awake = False
            _enter_sleep(voice, title, speak=True)
            continue

        voice.thinking()
        reply = spine.handle(spoken)
        voice.speak(reply)

"""Wake word and sleep phrase detection."""

from __future__ import annotations

DEFAULT_WAKE_PHRASES = (
    "spine wake up",
    "spine wakeup",
    "spine, wake up",
)

DEFAULT_SLEEP_PHRASES = (
    "spine sleep",
    "spine go silent",
    "go silent",
    "go to sleep",
    "standby",
    "sleep spine",
)


def _normalize(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()


def is_wake_phrase(text: str, phrases: tuple[str, ...] | None = None) -> bool:
    """Wake on 'Spine wake up' and close Whisper mis-hearings."""
    active = phrases or DEFAULT_WAKE_PHRASES
    normalized = _normalize(text)
    for phrase in active:
        if _normalize(phrase.replace(",", "")) in normalized:
            return True
    # Common mis-transcriptions
    wake_hints = ("spine wake", "spain wake", "spine wakeup", "spine wake up", "spine wikipedia")
    return any(hint in normalized for hint in wake_hints)


def is_sleep_phrase(text: str, phrases: tuple[str, ...] = DEFAULT_SLEEP_PHRASES) -> bool:
    normalized = _normalize(text)
    return any(p in normalized for p in phrases)


def wake_response(title: str = "Sir") -> str:
    return f"Awake and ready, {title}. How may I assist you?"


def sleep_response(title: str = "Sir") -> str:
    return f"Going silent, {title}. Say 'Spine, wake up' when you need me."

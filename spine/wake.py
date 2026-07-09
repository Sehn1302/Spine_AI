"""Wake word and sleep phrase detection."""

from __future__ import annotations

DEFAULT_WAKE_PHRASES = (
    "spine wake up",
    "spine wakeup",
    "spine, wake up",
    "wake up spine",
    "hey spine",
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


def is_wake_phrase(text: str, phrases: tuple[str, ...] = DEFAULT_WAKE_PHRASES) -> bool:
    normalized = _normalize(text)
    return any(p.replace(",", "") in normalized for p in phrases)


def is_sleep_phrase(text: str, phrases: tuple[str, ...] = DEFAULT_SLEEP_PHRASES) -> bool:
    normalized = _normalize(text)
    return any(p in normalized for p in phrases)


def wake_response(title: str = "Sir") -> str:
    return f"Awake and ready, {title}. How may I assist you?"


def sleep_response(title: str = "Sir") -> str:
    return f"Going silent, {title}. Say 'Spine, wake up' when you need me."

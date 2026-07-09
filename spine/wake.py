"""Wake word, sleep phrases, and 'Spine <command>' parsing."""

from __future__ import annotations

PREFIX_ALIASES = ("spine", "spain", "spike")

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


def parse_spine_command(text: str, prefix: str = "spine") -> str | None:
    """
    Extract command after 'Spine' prefix.
    'Spine launch minecraft' -> 'launch minecraft'
    Returns None if speech does not start with Spine (ignored).
    Returns '' if user only said 'Spine'.
    """
    if not text or not text.strip():
        return None

    normalized = _normalize(text)
    for alias in PREFIX_ALIASES:
        if normalized == alias:
            return ""
        if normalized.startswith(alias + " "):
            # Find where the command starts in original text (after prefix word)
            lowered = text.lower().lstrip()
            for sep in (alias + ",", alias + " "):
                if lowered.startswith(sep):
                    return text[len(sep) :].strip()
            if lowered.startswith(alias):
                return text[len(alias) :].strip().lstrip(",").strip()
    return None


def is_spine_invocation(text: str) -> bool:
    return parse_spine_command(text) is not None


def is_sleep_phrase(text: str, phrases: tuple[str, ...] = DEFAULT_SLEEP_PHRASES) -> bool:
    normalized = _normalize(text)
    return any(p in normalized for p in phrases)


def sleep_response(title: str = "Sir") -> str:
    return f"Going silent, {title}. Say 'Spine' followed by your command when you need me."

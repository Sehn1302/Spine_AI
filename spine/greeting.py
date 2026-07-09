"""Time-aware greetings and farewells for Spine."""

from __future__ import annotations

from datetime import datetime


def _period() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "evening"


def voice_greeting(title: str = "Sir") -> str:
    """Spoken when voice or visual mode starts."""
    period = _period()
    labels = {
        "morning": "Good morning",
        "afternoon": "Good afternoon",
        "evening": "Good evening",
    }
    return f"{labels[period]}, {title}. I am online. How may I assist you?"


def time_greeting(title: str = "Sir") -> str:
    """Printed when text mode starts."""
    period = _period()
    labels = {
        "morning": "Good morning",
        "afternoon": "Good afternoon",
        "evening": "Good evening",
    }
    return f"{labels[period]}, {title}. Spine is online. At your service."


def time_farewell(title: str = "Sir") -> str:
    period = _period()
    if period == "morning":
        return f"Very good, {title}. I shall remain available when you return. Have a productive day."
    if period == "afternoon":
        return f"Very good, {title}. I shall remain available when you return. Good afternoon."
    return f"Very good, {title}. I shall remain available when you return. Good evening."

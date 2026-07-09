"""Shared types and helpers for Spine specialist agents."""

from __future__ import annotations

from dataclasses import dataclass

import ollama


@dataclass
class AgentResult:
    agent: str
    summary: str
    details: str = ""


class BaseAgent:
    name = "base"
    description = "Base agent"

    def __init__(self, model: str, user_title: str = "Sir") -> None:
        self.model = model
        self.user_title = user_title

    def run(self, task: str) -> AgentResult:
        raise NotImplementedError

    def _ask(self, system: str, user: str) -> str:
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response["message"]["content"]

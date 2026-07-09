"""Spine orchestrator — conversation, memory, and Ollama integration."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ollama
import yaml

from persona import build_system_prompt

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    for key in ("memory", "conversations", "logs"):
        raw["paths"][key] = str((ROOT / raw["paths"][key]).resolve())

    return raw


def setup_logging(logs_dir: str) -> None:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(logs_dir) / f"spine_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


class SpineOrchestrator:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_config()
        setup_logging(self.config["paths"]["logs"])

        self.user_title = self.config["user"]["title"]
        self.model = self.config["spine"]["model"]
        self.spine_name = self.config["spine"]["name"]
        self.max_history = self.config["chat"]["max_history_messages"]

        self.conversations_dir = Path(self.config["paths"]["conversations"])
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        Path(self.config["paths"]["memory"]).mkdir(parents=True, exist_ok=True)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.conversations_dir / f"session_{self.session_id}.json"

        self.messages: list[dict[str, str]] = []
        self._load_latest_session()

        logging.info("Spine online — session %s, model %s", self.session_id, self.model)

    def _load_latest_session(self) -> None:
        sessions = sorted(self.conversations_dir.glob("session_*.json"))
        if not sessions:
            return

        latest = sessions[-1]
        try:
            with latest.open(encoding="utf-8") as handle:
                data = json.load(handle)
            self.messages = data.get("messages", [])
            self.session_id = data.get("session_id", self.session_id)
            self.session_file = latest
            logging.info("Resumed session %s (%d messages)", self.session_id, len(self.messages))
        except (json.JSONDecodeError, OSError) as exc:
            logging.warning("Could not load prior session: %s", exc)

    def _save_session(self) -> None:
        payload = {
            "session_id": self.session_id,
            "started_at": self.session_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "user_title": self.user_title,
            "model": self.model,
            "messages": self.messages,
        }
        with self.session_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def _build_ollama_messages(self) -> list[dict[str, str]]:
        system = {"role": "system", "content": build_system_prompt(self.user_title, self.spine_name)}
        recent = self.messages[-self.max_history :] if self.messages else []
        return [system, *recent]

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        try:
            response = ollama.chat(
                model=self.model,
                messages=self._build_ollama_messages(),
            )
            reply = response["message"]["content"]
        except Exception as exc:
            logging.error("Ollama request failed: %s", exc)
            reply = (
                f"My apologies, {self.user_title}. I am unable to reach the language model. "
                f"Please ensure Ollama is running and the model '{self.model}' is installed "
                f"(run: ollama pull {self.model})."
            )

        self.messages.append({"role": "assistant", "content": reply})
        self._save_session()
        logging.info("Exchange saved — %d messages in session", len(self.messages))
        return reply

    def new_session(self) -> None:
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.conversations_dir / f"session_{self.session_id}.json"
        self.messages = []
        self._save_session()
        logging.info("New session started: %s", self.session_id)

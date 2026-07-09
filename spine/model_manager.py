"""Model supervision — install, list, and run small LLMs under Spine."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

import ollama

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "model_catalog.json"

SMALL_MODEL_CATALOG: list[dict[str, Any]] = [
    {"name": "qwen2.5:7b", "ram_gb": 8, "vram_gb": 4, "role": "primary", "label": "Primary assistant"},
    {"name": "qwen2.5:3b", "ram_gb": 4, "vram_gb": 2, "role": "fast", "label": "Balanced small"},
    {"name": "phi3:mini", "ram_gb": 4, "vram_gb": 0, "role": "fast", "label": "Fast helper"},
    {"name": "gemma2:2b", "ram_gb": 4, "vram_gb": 0, "role": "tiny", "label": "Ultra-light"},
    {"name": "llama3.2:3b", "ram_gb": 4, "vram_gb": 2, "role": "fast", "label": "Compact"},
    {"name": "nomic-embed-text", "ram_gb": 2, "vram_gb": 0, "role": "embed", "label": "Knowledge embeddings"},
]


class ModelManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.config_path = Path(__file__).resolve().parent / "config.yaml"
        self.active_model = config.get("spine", {}).get("model", "qwen2.5:7b")
        self.embed_model = config.get("knowledge", {}).get("embed_model", "nomic-embed-text")
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> list[dict[str, Any]]:
        if CATALOG_PATH.exists():
            try:
                with CATALOG_PATH.open(encoding="utf-8") as handle:
                    return json.load(handle)
            except (json.JSONDecodeError, OSError):
                pass
        return SMALL_MODEL_CATALOG

    def list_installed(self) -> list[str]:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                return []
            names = []
            for line in result.stdout.splitlines()[1:]:
                parts = line.split()
                if parts:
                    names.append(parts[0])
            return names
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logging.warning("Could not list Ollama models: %s", exc)
            return []

    def pull(self, model_name: str) -> str:
        name = model_name.strip()
        if not name:
            return "Specify a model name to download."
        try:
            print(f"Downloading {name} — this may take several minutes...")
            result = subprocess.run(
                ["ollama", "pull", name],
                capture_output=True,
                text=True,
                check=False,
                timeout=3600,
            )
            if result.returncode != 0:
                return f"Download failed: {result.stderr.strip() or result.stdout.strip()}"
            return f"Model '{name}' is installed and ready."
        except FileNotFoundError:
            return "Ollama not found. Install from https://ollama.com/download"
        except subprocess.TimeoutExpired:
            return f"Download of '{name}' timed out. Try again."

    def set_active(self, model_name: str) -> str:
        name = model_name.strip()
        installed = self.list_installed()
        base = name.split(":")[0]
        if not any(m == name or m.startswith(f"{base}:") for m in installed):
            return f"Model '{name}' is not installed. Run: models pull {name}"

        content = self.config_path.read_text(encoding="utf-8")
        updated = re.sub(
            r"(spine:\s*\n\s*name:.*\n\s*)model:\s*.*",
            rf'\1model: "{name}"',
            content,
            count=1,
        )
        if updated == content:
            return "Could not update config.yaml."
        self.config_path.write_text(updated, encoding="utf-8")
        self.active_model = name
        self.config.setdefault("spine", {})["model"] = name
        return f"Active assistant model set to '{name}'."

    def recommend(self, ram_gb: int = 16, vram_gb: int = 0) -> str:
        lines = ["Recommended models for this PC:", ""]
        for entry in self.catalog:
            if entry.get("role") == "embed":
                continue
            needed = entry.get("ram_gb", 8)
            fit = "✓ fits" if ram_gb >= needed else "✗ needs more RAM"
            lines.append(f"  {entry['name']:<20} {entry.get('label', '')} — {fit}")
        lines.append("")
        if ram_gb >= 12:
            pick = "qwen2.5:7b"
        elif ram_gb >= 8:
            pick = "qwen2.5:3b"
        else:
            pick = "phi3:mini"
        lines.append(f"Suggested primary model: {pick}")
        lines.append("Commands: models pull <name> | models use <name> | models list")
        return "\n".join(lines)

    def status(self) -> str:
        installed = self.list_installed()
        lines = [
            f"Active model:  {self.active_model}",
            f"Embed model:   {self.embed_model}",
            "",
            f"Installed ({len(installed)}):",
        ]
        if installed:
            for name in installed:
                marker = " ← active" if name.split(":")[0] in self.active_model else ""
                lines.append(f"  {name}{marker}")
        else:
            lines.append("  (none — run Install Spine.bat or: models pull qwen2.5:7b)")

        lines.append("")
        lines.append("Spine supervises local LLMs via Ollama — all inference stays on your PC.")
        lines.append("  models list          — show installed models")
        lines.append("  models pull <name>   — download a model")
        lines.append("  models use <name>    — switch active assistant")
        lines.append("  models recommend     — hardware-based suggestions")
        return "\n".join(lines)

    def handle(self, task: str) -> str:
        parts = task.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else "list"
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command in {"list", "ls", "status"}:
            return self.status()
        if command == "pull":
            return self.pull(argument)
        if command in {"use", "set", "switch"}:
            return self.set_active(argument)
        if command in {"recommend", "suggest"}:
            return self.recommend()
        if command == "help":
            return self.status()
        return (
            f"Unknown models command '{command}'. "
            "Use: models list | pull <name> | use <name> | recommend"
        )

    def test_model(self, model_name: str) -> str:
        try:
            response = ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": "Reply with exactly: online"}],
            )
            reply = response["message"]["content"].strip()
            return f"Model '{model_name}' responded: {reply[:80]}"
        except Exception as exc:
            return f"Model test failed: {exc}"

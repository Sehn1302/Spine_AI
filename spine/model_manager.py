"""Model supervision — multi-LLM brain routing, bench, custom models."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import ollama

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "model_catalog.json"
MODelfile_DIR = ROOT / "memory" / "modelfiles"

SMALL_MODEL_CATALOG: list[dict[str, Any]] = [
    {"name": "qwen2.5:7b", "ram_gb": 8, "vram_gb": 4, "role": "primary", "label": "Primary brain"},
    {"name": "qwen2.5:3b", "ram_gb": 4, "vram_gb": 2, "role": "fast", "label": "Balanced small"},
    {"name": "phi3:mini", "ram_gb": 4, "vram_gb": 0, "role": "fast", "label": "Fast module"},
    {"name": "gemma2:2b", "ram_gb": 4, "vram_gb": 0, "role": "tiny", "label": "Ultra-light"},
    {"name": "llama3.2:3b", "ram_gb": 4, "vram_gb": 2, "role": "fast", "label": "Compact"},
    {"name": "nomic-embed-text", "ram_gb": 2, "vram_gb": 0, "role": "embed", "label": "Memory embeddings"},
]


class ModelManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.config_path = Path(__file__).resolve().parent / "config.yaml"
        models_cfg = config.get("models", {})
        self.primary = models_cfg.get("primary", config.get("spine", {}).get("model", "qwen2.5:7b"))
        self.fast = models_cfg.get("fast", "phi3:mini")
        self.routing = models_cfg.get("routing", {})
        self.active_model = config.get("spine", {}).get("model", self.primary)
        self.embed_model = config.get("knowledge", {}).get("embed_model", "nomic-embed-text")
        self.catalog = self._load_catalog()
        self._bench_cache: dict[str, float] = {}

    def _resolve_name(self, ref: str) -> str:
        lowered = ref.strip().lower()
        if lowered in {"primary", "main", "smart", "brain"}:
            return self.primary
        if lowered in {"fast", "quick", "light"}:
            return self.fast
        return ref.strip()

    def model_for_role(self, role: str) -> str:
        ref = self.routing.get(role, "primary")
        if isinstance(ref, str):
            return self._resolve_name(ref)
        return self.primary

    def routing_report(self) -> str:
        lines = [
            "Multi-LLM brain routing:",
            f"  Primary: {self.primary}",
            f"  Fast:    {self.fast}",
            f"  Chat:    {self.model_for_role('chat')} (active: {self.active_model})",
            "",
            "Per-agent modules:",
        ]
        for role in ("pc", "research", "study", "files", "planner"):
            lines.append(f"  {role:<10} -> {self.model_for_role(role)}")
        lines.append(f"  embed      -> {self.embed_model}")
        return "\n".join(lines)

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
            return [line.split()[0] for line in result.stdout.splitlines()[1:] if line.split()]
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logging.warning("Could not list Ollama models: %s", exc)
            return []

    def pull(self, model_name: str) -> str:
        name = self._resolve_name(model_name)
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
        name = self._resolve_name(model_name)
        installed = self.list_installed()
        base = name.split(":")[0]
        if not any(m == name or m.startswith(f"{base}:") for m in installed):
            return f"Model '{name}' is not installed. Run: models pull {name}"

        content = self.config_path.read_text(encoding="utf-8")
        updated = re.sub(
            r"(^\s*model:\s*)\".*?\"",
            rf'\1"{name}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if updated == content:
            return "Could not update config.yaml."
        self.config_path.write_text(updated, encoding="utf-8")
        self.active_model = name
        self.config.setdefault("spine", {})["model"] = name
        return f"Active chat model set to '{name}'. Agent routing unchanged — say 'models routing' to view."

    def recommend(self, ram_gb: int = 16, vram_gb: int = 4) -> str:
        lines = ["Recommended models for this PC:", ""]
        for entry in self.catalog:
            if entry.get("role") == "embed":
                continue
            needed = entry.get("ram_gb", 8)
            fit = "fits" if ram_gb >= needed else "needs more RAM"
            lines.append(f"  {entry['name']:<20} {entry.get('label', '')} — {fit}")
        lines.append("")
        lines.append(f"Suggested primary: {self.primary}")
        lines.append(f"Suggested fast:    {self.fast}")
        lines.append(self.routing_report())
        return "\n".join(lines)

    def bench(self) -> str:
        installed = [m for m in self.list_installed() if "embed" not in m.lower()]
        if not installed:
            return "No models installed. Run: models pull qwen2.5:7b"

        lines = ["Model benchmark (latency + response):", ""]
        for name in installed:
            start = time.perf_counter()
            try:
                response = ollama.chat(
                    model=name,
                    messages=[{"role": "user", "content": "Reply with one word: online"}],
                )
                elapsed = time.perf_counter() - start
                reply = response["message"]["content"].strip()[:40]
                self._bench_cache[name] = elapsed
                lines.append(f"  {name:<22} {elapsed:5.2f}s  — {reply}")
            except Exception as exc:
                lines.append(f"  {name:<22} FAIL  — {exc}")

        if self._bench_cache:
            best = min(self._bench_cache, key=self._bench_cache.get)
            lines.append("")
            lines.append(f"Fastest: {best} ({self._bench_cache[best]:.2f}s)")
        return "\n".join(lines)

    def create_custom_model(self, name: str, base: str = "") -> str:
        """Build Ollama Modelfile from knowledge notes — starter for custom brain."""
        base_model = self._resolve_name(base or self.primary)
        MODelfile_DIR.mkdir(parents=True, exist_ok=True)
        knowledge_dir = Path(self.config["paths"]["knowledge"])
        snippets: list[str] = []
        for path in sorted(knowledge_dir.glob("*.txt"))[:5]:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:1500]
                snippets.append(f"# From {path.name}\n{text}")
            except OSError:
                continue

        system = (
            "You are Spine, a personal assistant trained on the user's own notes. "
            "Be formal, concise, and helpful."
        )
        if snippets:
            system += "\n\nUser knowledge:\n" + "\n---\n".join(snippets)

        modelfile = MODelfile_DIR / f"{name}.Modelfile"
        modelfile.write_text(
            f'FROM {base_model}\n\nSYSTEM """{system}"""\n\nPARAMETER temperature 0.7\n',
            encoding="utf-8",
        )

        result = subprocess.run(
            ["ollama", "create", name, "-f", str(modelfile)],
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        if result.returncode != 0:
            return f"Create failed: {result.stderr or result.stdout}"
        return (
            f"Custom model '{name}' created from {base_model} + your knowledge notes.\n"
            f"Modelfile: {modelfile}\n"
            f"Use: models use {name}"
        )

    def status(self) -> str:
        installed = self.list_installed()
        lines = [
            f"Active chat model: {self.active_model}",
            f"Embed model:       {self.embed_model}",
            "",
            self.routing_report(),
            "",
            f"Installed ({len(installed)}):",
        ]
        for mname in installed:
            marker = " ← chat" if mname.split(":")[0] in self.active_model else ""
            lines.append(f"  {mname}{marker}")
        lines.extend([
            "",
            "Commands:",
            "  models list | routing | pull <name> | use <name|fast|primary>",
            "  models bench | recommend | train <custom-name>",
        ])
        return "\n".join(lines)

    def handle(self, task: str) -> str:
        parts = task.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else "list"
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command in {"list", "ls", "status"}:
            return self.status()
        if command in {"routing", "brain", "map"}:
            return self.routing_report()
        if command == "pull":
            return self.pull(argument)
        if command in {"use", "set", "switch"}:
            return self.set_active(argument)
        if command in {"recommend", "suggest"}:
            return self.recommend()
        if command in {"bench", "benchmark", "test"}:
            return self.bench()
        if command == "train":
            return self.create_custom_model(argument or "spine-custom")
        if command == "help":
            return self.status()
        return (
            f"Unknown models command '{command}'. "
            "Use: list | routing | pull | use | bench | train | recommend"
        )

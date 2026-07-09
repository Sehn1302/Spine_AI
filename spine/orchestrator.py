"""Spine orchestrator — conversation, memory, and Ollama integration."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ollama
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents import FilesAgent, PcAgent, ResearchAgent, StudyAgent
from action_log import ActionLog
from host_capabilities import HostCapabilities
from knowledge import KnowledgeBase
from model_manager import ModelManager
from persona import build_system_prompt
from scheduler import TaskScheduler, handle_schedule_command


def load_config() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    for key in ("memory", "conversations", "knowledge", "chroma", "logs"):
        value = raw["paths"][key]
        path = Path(value)
        raw["paths"][key] = str(path if path.is_absolute() else (ROOT / value).resolve())

    host_cfg = raw.get("host", {})
    if host_cfg.get("cache_path"):
        cache = Path(host_cfg["cache_path"])
        host_cfg["cache_path"] = str(cache if cache.is_absolute() else (ROOT / host_cfg["cache_path"]).resolve())
        raw["host"] = host_cfg

    return raw


def setup_logging(logs_dir: str, *, quiet: bool = False) -> None:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(logs_dir) / f"spine_{datetime.now().strftime('%Y%m%d')}.log"
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if logging.getLogger().handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(fmt)
        logging.getLogger().addHandler(handler)
        return

    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    if not quiet:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )


class SpineOrchestrator:
    def __init__(self, config: dict[str, Any] | None = None, *, quiet: bool = False) -> None:
        self.config = config or load_config()
        self.quiet = quiet
        setup_logging(self.config["paths"]["logs"], quiet=quiet)
        self.action_log = ActionLog(self.config["paths"]["logs"])

        self.user_title = self.config["user"]["title"]
        self.models = ModelManager(self.config)
        self.model = self.models.model_for_role("chat")
        self.spine_name = self.config["spine"]["name"]
        self.max_history = self.config["chat"]["max_history_messages"]

        self.conversations_dir = Path(self.config["paths"]["conversations"])
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        Path(self.config["paths"]["memory"]).mkdir(parents=True, exist_ok=True)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.conversations_dir / f"session_{self.session_id}.json"

        self.messages: list[dict[str, str]] = []
        self._load_latest_session()

        knowledge_cfg = self.config.get("knowledge", {})
        self.knowledge = KnowledgeBase(
            knowledge_dir=self.config["paths"]["knowledge"],
            chroma_dir=self.config["paths"]["chroma"],
            embed_model=knowledge_cfg.get("embed_model", "nomic-embed-text"),
            chunk_size=knowledge_cfg.get("chunk_size", 800),
            chunk_overlap=knowledge_cfg.get("chunk_overlap", 100),
            top_k=knowledge_cfg.get("top_k", 4),
        )

        logging.info("Spine online — session %s, chat model %s", self.session_id, self.model)
        logging.info("Knowledge base ready — %d indexed chunks", self.knowledge.document_count)
        logging.info("%s", self.models.routing_report().replace("\n", " | "))

        if knowledge_cfg.get("auto_index_on_startup", False):
            try:
                stats = self.knowledge.index_all()
                logging.info(
                    "Auto-indexed knowledge: %d new, %d chunks total",
                    stats.get("indexed", 0),
                    stats.get("total_chunks", 0),
                )
            except Exception as exc:
                logging.warning("Auto-index skipped: %s", exc)

        host_cfg = self.config.get("host", {})
        self.host_caps = HostCapabilities(
            cache_path=host_cfg.get("cache_path"),
            rescan_hours=host_cfg.get("rescan_hours", 24),
        )
        if host_cfg.get("scan_on_startup", False):
            self.host_caps.load_or_scan()
            if not self.quiet:
                print(self.host_caps.format_report())
                print()

        pc_cfg = self.config.get("pc", {})
        self._init_agents(pc_cfg)
        self.scheduler: TaskScheduler | None = None
        sched_cfg = self.config.get("scheduler", {})
        if sched_cfg.get("enabled", True):
            self.scheduler = TaskScheduler(
                self._run_scheduled_command,
                interval=sched_cfg.get("check_interval_seconds", 60),
            )
            self.scheduler.start()

    def _init_agents(self, pc_cfg: dict) -> None:
        m = self.models
        self.agents = {
            "research": ResearchAgent(m.model_for_role("research"), self.user_title),
            "study": StudyAgent(m.model_for_role("study"), self.user_title),
            "files": FilesAgent(m.model_for_role("files"), self.user_title),
            "pc": PcAgent(
                m.model_for_role("planner"),
                self.user_title,
                action_log=self.action_log,
                host_caps=self.host_caps,
                unrestricted=pc_cfg.get("unrestricted", True),
            ),
        }

    def _run_scheduled_command(self, command: str) -> str:
        logging.info("Scheduled command: %s", command)
        if command == "index":
            return self.index_knowledge()
        return self.handle(command)

    def sync_agent_models(self) -> None:
        self.config = load_config()
        self.models = ModelManager(self.config)
        self.model = self.models.model_for_role("chat")
        pc_cfg = self.config.get("pc", {})
        if not hasattr(self, "host_caps"):
            host_cfg = self.config.get("host", {})
            self.host_caps = HostCapabilities(
                cache_path=host_cfg.get("cache_path"),
                rescan_hours=host_cfg.get("rescan_hours", 24),
            )
        self._init_agents(pc_cfg)

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

    def _build_ollama_messages(self, user_input: str | None = None) -> list[dict[str, str]]:
        host_context = self.host_caps.format_for_prompt() if hasattr(self, "host_caps") else ""
        system_content = build_system_prompt(self.user_title, self.spine_name, host_context=host_context)

        if user_input:
            hits = self.knowledge.search(user_input)
            context = self.knowledge.format_context(hits)
            if context:
                system_content += (
                    f"\n\nRelevant knowledge from {self.user_title}'s files "
                    f"(cite the source when used):\n\n{context}"
                )

        system = {"role": "system", "content": system_content}
        recent = self.messages[-self.max_history :] if self.messages else []
        return [system, *recent]

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        try:
            response = ollama.chat(
                model=self.model,
                messages=self._build_ollama_messages(user_input),
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

    def index_knowledge(self) -> str:
        try:
            stats = self.knowledge.index_all()
        except Exception as exc:
            logging.error("Knowledge indexing failed: %s", exc)
            return (
                f"My apologies, {self.user_title}. Knowledge indexing failed. "
                f"Ensure Ollama is running and the embedding model is installed "
                f"(run: ollama pull {self.knowledge.embed_model})."
            )

        return (
            f"Knowledge base updated, {self.user_title}. "
            f"Indexed {stats['indexed']} file(s), skipped {stats['skipped']} unchanged, "
            f"{stats['total_chunks']} total chunk(s) available."
        )

    def remember(self, text: str) -> str:
        if not text.strip():
            return f"Please provide text to remember, {self.user_title}."

        try:
            filename = self.knowledge.add_note(text)
        except Exception as exc:
            logging.error("Failed to save note: %s", exc)
            return f"My apologies, {self.user_title}. I could not save that note."

        return (
            f"Noted, {self.user_title}. Saved to memory/knowledge/{filename}. "
            f"I shall recall it in future conversations."
        )

    def delegate(self, agent_name: str, task: str) -> str:
        agent = self.agents.get(agent_name)
        if not agent:
            return f"Unknown agent '{agent_name}', {self.user_title}."

        self.messages.append({"role": "user", "content": f"[{agent_name}] {task}"})
        logging.info("Delegating to %s agent: %s", agent_name, task)

        try:
            if agent_name == "study":
                hits = self.knowledge.search(task)
                context = self.knowledge.format_context(hits)
                result = agent.run(task, knowledge_context=context)
            else:
                result = agent.run(task)
        except Exception as exc:
            logging.error("Agent %s failed: %s", agent_name, exc)
            reply = (
                f"My apologies, {self.user_title}. The {agent_name} agent encountered an error. "
                "Please try again shortly."
            )
            self.messages.append({"role": "assistant", "content": reply})
            self._save_session()
            return reply

        reply = (
            f"Routing complete, {self.user_title}. The {agent_name.title()} module reports:\n\n"
            f"{result.summary}"
        )
        self.messages.append({"role": "assistant", "content": reply})
        self._save_session()
        logging.info("Agent %s completed task", agent_name)
        return reply

    def confirm_pending(self) -> str:
        pc_agent: PcAgent = self.agents["pc"]
        self.messages.append({"role": "user", "content": "[confirm]"})
        result = pc_agent.apply_pending()
        reply = result.summary
        self.messages.append({"role": "assistant", "content": reply})
        self._save_session()
        return reply

    def cancel_pending(self) -> str:
        pc_agent: PcAgent = self.agents["pc"]
        self.messages.append({"role": "user", "content": "[cancel]"})
        result = pc_agent.cancel_pending()
        reply = result.summary
        self.messages.append({"role": "assistant", "content": reply})
        self._save_session()
        return reply

    def handle_models(self, task: str) -> str:
        reply = self.models.handle(task)
        if task.strip().lower().startswith(("use ", "set ", "switch ")):
            self.sync_agent_models()
        self.messages.append({"role": "user", "content": f"[models] {task}"})
        self.messages.append({"role": "assistant", "content": reply})
        self._save_session()
        return reply

    def handle(self, user_input: str) -> str:
        lowered = user_input.lower().strip()
        if lowered in {"confirm", "yes"}:
            return self.confirm_pending()
        if lowered in {"cancel", "no", "abort"}:
            return self.cancel_pending()

        if lowered == "models" or lowered.startswith("models "):
            task = user_input[6:].strip() if lowered.startswith("models ") else "list"
            return self.handle_models(task)

        if lowered == "schedule" or lowered.startswith("schedule "):
            task = user_input[9:].strip() if lowered.startswith("schedule ") else "list"
            reply = handle_schedule_command(task)
            self.messages.append({"role": "user", "content": f"[schedule] {task}"})
            self.messages.append({"role": "assistant", "content": reply})
            self._save_session()
            return reply

        if lowered in {"index", "reindex"}:
            return self.index_knowledge()

        route = parse_agent_command(user_input)
        if route:
            agent_name, task = route
            if agent_name == "remember":
                reply = self.remember(task)
                self.messages.append({"role": "user", "content": user_input})
                self.messages.append({"role": "assistant", "content": reply})
                self._save_session()
                return reply
            if agent_name == "models":
                return self.handle_models(task)
            if agent_name == "schedule":
                reply = handle_schedule_command(task)
                self.messages.append({"role": "user", "content": f"[schedule] {task}"})
                self.messages.append({"role": "assistant", "content": reply})
                self._save_session()
                return reply
            return self.delegate(agent_name, task)

        pc_cfg = self.config.get("pc", {})
        if pc_cfg.get("auto_control", True) and wants_pc_control(user_input):
            return self.delegate("pc", f"do {user_input}")

        return self.chat(user_input)

    def new_session(self) -> None:
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.conversations_dir / f"session_{self.session_id}.json"
        self.messages = []
        self._save_session()
        logging.info("New session started: %s", self.session_id)

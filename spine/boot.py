"""Boot-time health checks — Ollama, single instance, logging."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_FILE = ROOT / "memory" / ".spine_running"


def boot_log_path(logs_dir: str) -> Path:
    return Path(logs_dir) / "boot.log"


def setup_boot_logging(logs_dir: str) -> None:
    """File-only logging for silent pythonw startup."""
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    boot_file = boot_log_path(logs_dir)
    handlers: list[logging.Handler] = [logging.FileHandler(boot_file, encoding="utf-8")]
    if sys.stdout and hasattr(sys.stdout, "write"):
        try:
            handlers.append(logging.StreamHandler())
        except Exception:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.info("Boot logging initialized → %s", boot_file)


def log_boot(msg: str) -> None:
    logging.info(msg)


def ensure_single_instance() -> bool:
    """Return False if another Spine instance is already running."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            if _pid_alive(old_pid):
                logging.warning("Spine already running (PID %s). Exiting duplicate.", old_pid)
                return False
            LOCK_FILE.unlink(missing_ok=True)
        except (ValueError, OSError):
            LOCK_FILE.unlink(missing_ok=True)

    try:
        import errno

        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        logging.info("Single instance lock acquired (PID %s)", os.getpid())
        return True
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            logging.warning("Spine startup lock busy — another instance starting.")
            return False
        raise


def release_instance_lock() -> None:
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text(encoding="utf-8").strip() == str(os.getpid()):
            LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def ensure_gpu_env() -> None:
    """Ensure Ollama and CUDA libraries can use the GPU."""
    os.environ.pop("OLLAMA_NO_GPU", None)
    os.environ.setdefault("OLLAMA_NUM_GPU", "1")


def log_gpu_status() -> None:
    """Log CUDA / Ollama processor info for boot diagnostics."""
    ensure_gpu_env()
    try:
        import ctranslate2

        count = ctranslate2.get_cuda_device_count()
        logging.info("CUDA devices available (Whisper): %d", count)
    except Exception as exc:
        logging.warning("CUDA check failed: %s", exc)

    logging.info(
        "Ollama env — OLLAMA_NO_GPU=%r, OLLAMA_NUM_GPU=%r",
        os.environ.get("OLLAMA_NO_GPU", ""),
        os.environ.get("OLLAMA_NUM_GPU", ""),
    )

    try:
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                logging.info("Ollama: %s", line.strip())
        else:
            logging.info("Ollama: no models loaded yet (GPU activates when you ask Spine something)")
    except Exception as exc:
        logging.debug("Ollama ps skipped: %s", exc)


def start_ollama_app() -> None:
    """Launch Ollama tray app if installed (starts the server on Windows)."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "Ollama.exe",
        Path("C:/Program Files/Ollama/Ollama.exe"),
    ]
    for path in candidates:
        if path.exists():
            try:
                env = os.environ.copy()
                env.pop("OLLAMA_NO_GPU", None)
                env.setdefault("OLLAMA_NUM_GPU", "1")
                subprocess.Popen(
                    [str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                logging.info("Started Ollama: %s", path)
                return
            except OSError as exc:
                logging.warning("Could not start Ollama: %s", exc)
    logging.warning("Ollama.exe not found — ensure Ollama is installed.")


def wait_for_ollama(timeout_seconds: int = 90) -> bool:
    """Poll until Ollama API responds."""
    start_ollama_app()
    deadline = time.time() + timeout_seconds
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                logging.info("Ollama ready (attempt %d)", attempt)
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logging.debug("Ollama wait: %s", exc)
        time.sleep(3)
    logging.error("Ollama not ready after %ds", timeout_seconds)
    return False


def wait_for_audio(seconds: float = 12.0) -> None:
    """Give Windows audio drivers and display time after login."""
    logging.info("Waiting %.0fs for audio/display drivers...", seconds)
    time.sleep(seconds)


def preload_voice(voice) -> bool:
    """Load Whisper before first listen so wake phrase isn't missed."""
    try:
        logging.info("Preloading speech recognition model...")
        voice._get_whisper()
        logging.info("Speech model ready.")
        return True
    except Exception as exc:
        logging.error("Speech model failed to load: %s", exc)
        return False

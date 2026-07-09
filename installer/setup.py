"""Spine AI installer — checks system, installs deps, pulls models, configures."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
PYTHON = VENV / "Scripts" / "python.exe"
PIP = VENV / "Scripts" / "pip.exe"
FLAG = ROOT / ".spine_installed"
CONFIG = ROOT / "spine" / "config.yaml"
REQUIREMENTS = ROOT / "requirements.txt"

DEFAULT_MODELS = ("qwen2.5:7b", "nomic-embed-text")
SMALL_MODEL_CATALOG = (
    {"name": "qwen2.5:7b", "ram_gb": 8, "label": "Primary assistant (7B)"},
    {"name": "phi3:mini", "ram_gb": 4, "label": "Fast helper (3.8B)"},
    {"name": "gemma2:2b", "ram_gb": 4, "label": "Lightweight (2B)"},
    {"name": "llama3.2:3b", "ram_gb": 4, "label": "Compact (3B)"},
    {"name": "qwen2.5:3b", "ram_gb": 4, "label": "Balanced small (3B)"},
)


def banner(title: str) -> None:
    print()
    print("  " + "=" * 60)
    print(f"  {title}")
    print("  " + "=" * 60)
    print()


def step(num: int, total: int, msg: str) -> None:
    print(f"  [{num}/{total}] {msg}")


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"       > {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check, text=True)


def find_python() -> str:
    for candidate in ("py -3.11", "py -3", "python"):
        try:
            result = subprocess.run(
                candidate.split() + ["--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and "3." in (result.stdout + result.stderr):
                return candidate.split()[0] if " " not in candidate else candidate
        except FileNotFoundError:
            continue
    return ""


def check_ollama() -> bool:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False, timeout=30)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def create_venv(py_cmd: str) -> None:
    if PYTHON.exists():
        print("       Virtual environment already exists.")
        return
    if py_cmd == "py -3.11":
        run(["py", "-3.11", "-m", "venv", str(VENV)])
    elif py_cmd == "py -3":
        run(["py", "-3", "-m", "venv", str(VENV)])
    else:
        run([py_cmd, "-m", "venv", str(VENV)])


def install_requirements() -> None:
    run([str(PIP), "install", "--upgrade", "pip"], check=False)
    run([str(PIP), "install", "-r", str(REQUIREMENTS)])


def pull_models(models: tuple[str, ...]) -> None:
    for model in models:
        print(f"       Downloading {model} (this may take several minutes)...")
        run(["ollama", "pull", model])


def detect_ram_gb() -> int:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        return int(float(result.stdout.strip()))
    except Exception:
        return 16


def pick_recommended_model(ram_gb: int) -> str:
    if ram_gb >= 12:
        return "qwen2.5:7b"
    if ram_gb >= 8:
        return "qwen2.5:3b"
    return "phi3:mini"


def update_config_model(model_name: str, user_title: str = "Sir") -> None:
    import re

    content = CONFIG.read_text(encoding="utf-8")
    content = re.sub(
        r'(spine:\s*\n\s*name:\s*"[^"]*"\s*\n\s*)model:\s*[^\n]+',
        rf'\1model: "{model_name}"',
        content,
        count=1,
    )
    content = re.sub(r'(user:\s*\n\s*)title:\s*"[^"]*"', rf'\1title: "{user_title}"', content, count=1)
    CONFIG.write_text(content, encoding="utf-8")


def write_catalog() -> None:
    catalog_path = ROOT / "data" / "model_catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with catalog_path.open("w", encoding="utf-8") as handle:
        json.dump(SMALL_MODEL_CATALOG, handle, indent=2)


def create_desktop_shortcut() -> None:
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if not desktop.exists():
        return
    shortcut = desktop / "Launch Spine.bat"
    if shortcut.exists():
        return
    try:
        shutil.copy2(ROOT / "Launch Spine.bat", shortcut)
        print(f"       Desktop shortcut: {shortcut}")
    except OSError as exc:
        print(f"       Could not create desktop shortcut: {exc}")


def ensure_dirs() -> None:
    for folder in ("memory/knowledge", "memory/conversations", "memory/chroma", "logs"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    keep = ROOT / "memory" / "knowledge" / ".gitkeep"
    if not keep.exists():
        keep.touch()


def main() -> int:
    total = 8
    banner("SPINE AI — INSTALLER")

    step(1, total, "Checking Python 3.11+")
    py_cmd = find_python()
    if not py_cmd:
        print("  ERROR: Python 3.11+ not found. Install from https://python.org")
        return 1
    print(f"       Found: {py_cmd}")

    step(2, total, "Creating virtual environment")
    create_venv(py_cmd)

    step(3, total, "Installing Python packages")
    install_requirements()

    step(4, total, "Checking Ollama")
    if not check_ollama():
        print()
        print("  Ollama is required for Spine's brain.")
        print("  Download from: https://ollama.com/download")
        print("  After installing Ollama, run this installer again.")
        return 1
    print("       Ollama is running.")

    step(5, total, "Detecting hardware and choosing model")
    ram_gb = detect_ram_gb()
    recommended = pick_recommended_model(ram_gb)
    print(f"       RAM: ~{ram_gb} GB — recommended model: {recommended}")

    title = input("       How should Spine address you? [Sir]: ").strip() or "Sir"

    step(6, total, "Downloading AI models")
    models = (recommended, "nomic-embed-text")
    if recommended not in DEFAULT_MODELS:
        pull_models(models)
    else:
        pull_models(DEFAULT_MODELS)

    step(7, total, "Writing configuration")
    update_config_model(recommended, title)
    write_catalog()
    ensure_dirs()
    create_desktop_shortcut()

    step(8, total, "Finalizing")
    FLAG.write_text(
        json.dumps({"model": recommended, "title": title, "ram_gb": ram_gb}, indent=2),
        encoding="utf-8",
    )

    banner("INSTALLATION COMPLETE")
    print(f"  Spine is ready, {title}.")
    print(f"  Active model: {recommended}")
    print()
    print("  Double-click 'Launch Spine.bat' to start your assistant.")
    print("  Say 'Spine, wake up' to activate voice mode.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

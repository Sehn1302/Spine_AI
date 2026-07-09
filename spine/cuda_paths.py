"""Ensure NVIDIA CUDA 12 DLLs from pip packages are visible on Windows."""

from __future__ import annotations

import logging
import os
import site
import sys
from pathlib import Path

_applied = False


def ensure_cuda_dll_path() -> None:
    """Prepend nvidia-*-cu12 package bin dirs to PATH for CTranslate2."""
    global _applied
    if _applied or sys.platform != "win32":
        return

    candidates: list[str] = []
    search_roots: list[Path] = []

    for entry in site.getsitepackages():
        search_roots.append(Path(entry))
    user_site = site.getusersitepackages()
    if user_site:
        search_roots.append(Path(user_site))

    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        search_roots.append(Path(venv) / "Lib" / "site-packages")

    for root in search_roots:
        nvidia_root = root / "nvidia"
        if not nvidia_root.is_dir():
            continue
        for package_dir in sorted(nvidia_root.iterdir()):
            bin_dir = package_dir / "bin"
            if bin_dir.is_dir():
                candidates.append(str(bin_dir))

    if not candidates:
        logging.debug("No NVIDIA pip CUDA bin directories found.")
        _applied = True
        return

    path = os.environ.get("PATH", "")
    missing = [entry for entry in candidates if entry not in path.split(";")]
    if missing:
        os.environ["PATH"] = ";".join(missing) + (";" + path if path else "")
        logging.info("CUDA DLL path added for Whisper: %s", ", ".join(missing))

    if hasattr(os, "add_dll_directory"):
        for entry in candidates:
            try:
                os.add_dll_directory(entry)
            except OSError:
                pass

    _applied = True

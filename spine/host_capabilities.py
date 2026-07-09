"""Detect host PC software and hardware — adapts Spine to whatever machine it runs on."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import winreg
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sounddevice as sd

ROOT = Path(__file__).resolve().parent.parent

CAPABILITY_SIGNATURES: dict[str, dict[str, Any]] = {
    "armoury_crate": {
        "display": "ASUS Armoury Crate",
        "markers": ["armoury crate", "armory crate", "asus system control interface"],
        "registry": [r"SOFTWARE\ASUS", r"SOFTWARE\ASUSTeK"],
        "paths": [
            r"C:\Program Files\ASUS\ARMOURY CRATE",
            r"C:\Program Files (x86)\ASUS\ARMOURY CRATE",
        ],
        "launch": ["armoury crate"],
        "audio_markers": ["ai noise cancel", "asus utility", "fortemedia"],
        "category": "audio",
        "notes": "Two-Way AI Noise Cancellation and ASUS device control.",
    },
    "realtek_audio": {
        "display": "Realtek Audio Console",
        "markers": ["realtek audio console", "realtek audio"],
        "paths": [
            r"C:\Program Files\Realtek\Audio\HDA\RtkNGUI64.exe",
            r"C:\Program Files\Realtek\Audio\HDA\RAVCpl64.exe",
        ],
        "launch": ["realtek audio console"],
        "audio_markers": ["realtek", "enhance voice"],
        "category": "audio",
        "notes": "Onboard audio tuning; pairs with vendor noise cancellation.",
    },
    "g_helper": {
        "display": "G-Helper",
        "markers": ["g-helper", "ghelper"],
        "paths": [r"C:\Program Files\G-Helper\GHelper.exe"],
        "launch": [r"C:\Program Files\G-Helper\GHelper.exe"],
        "category": "system",
        "notes": "Lightweight ASUS laptop control (alternative to Armoury Crate).",
    },
    "dell_audio": {
        "display": "Dell / Waves MaxxAudio",
        "markers": ["waves maxxaudio", "dell audio", "alienware audio", "maxxaudiopro"],
        "paths": [
            r"C:\Program Files\Waves\MaxxAudio",
            r"C:\Program Files\Dell\DellAudio",
        ],
        "launch": ["waves maxxaudio pro"],
        "audio_markers": ["waves maxx", "maxxaudio"],
        "category": "audio",
        "notes": "Dell and Alienware audio enhancement suite.",
    },
    "lenovo_vantage": {
        "display": "Lenovo Vantage",
        "markers": ["lenovo vantage"],
        "paths": [r"C:\Program Files (x86)\Lenovo\VantageService"],
        "launch": ["lenovo vantage"],
        "category": "system",
        "notes": "Lenovo system settings, updates, and audio profiles.",
    },
    "nvidia_broadcast": {
        "display": "NVIDIA Broadcast",
        "markers": ["nvidia broadcast"],
        "paths": [
            r"C:\Program Files\NVIDIA Corporation\NVIDIA Broadcast\NVIDIA Broadcast.exe",
        ],
        "launch": ["nvidia broadcast"],
        "audio_markers": ["nvidia broadcast"],
        "category": "audio",
        "notes": "AI noise removal and virtual background for mic and camera.",
    },
    "amd_adrenalin": {
        "display": "AMD Adrenalin",
        "markers": ["amd software", "amd adrenalin", "radeon software"],
        "paths": [r"C:\Program Files\AMD\CNext\CNext"],
        "launch": ["amd software"],
        "audio_markers": ["amd noise suppression"],
        "category": "system",
        "notes": "AMD GPU control; includes noise suppression on supported hardware.",
    },
    "dolby_atmos": {
        "display": "Dolby Atmos",
        "markers": ["dolby atmos", "dolby access"],
        "paths": [r"C:\Program Files\Dolby\DolbyAccess"],
        "launch": ["dolby access"],
        "audio_markers": ["dolby atmos"],
        "category": "audio",
        "notes": "Spatial audio and Dolby voice processing.",
    },
    "intel_unison": {
        "display": "Intel Unison",
        "markers": ["intel unison"],
        "launch": ["intel unison"],
        "category": "connectivity",
        "notes": "Phone-to-PC connectivity and notifications.",
    },
    "steelseries_gg": {
        "display": "SteelSeries GG",
        "markers": ["steelseries gg", "steelseries engine"],
        "launch": ["steelseries gg"],
        "category": "peripheral",
        "notes": "SteelSeries headset and peripheral control.",
    },
    "icue": {
        "display": "Corsair iCUE",
        "markers": ["icue", "corsair icue"],
        "launch": ["icue"],
        "category": "peripheral",
        "notes": "Corsair RGB and audio device control.",
    },
    "logitech_g_hub": {
        "display": "Logitech G HUB",
        "markers": ["logitech g hub", "lghub"],
        "paths": [r"C:\Program Files\LGHUB\lghub.exe"],
        "launch": ["lghub", "logitech g hub"],
        "category": "peripheral",
        "notes": "Logitech headset and peripheral profiles.",
    },
    "microsoft_teams": {
        "display": "Microsoft Teams",
        "markers": ["microsoft teams"],
        "launch": ["ms-teams"],
        "category": "communication",
        "notes": "Built-in voice isolation when used as comms app.",
    },
}

_ENHANCED_AUDIO_MARKERS = (
    "ai noise cancel",
    "noise cancel",
    "noise suppression",
    "asus utility",
    "nvidia broadcast",
    "krisp",
    "fortemedia",
    "waves maxx",
    "dolby voice",
    "amd noise",
)


@dataclass
class DetectedCapability:
    key: str
    display: str
    category: str
    notes: str
    launch_targets: list[str] = field(default_factory=list)
    audio_devices: list[str] = field(default_factory=list)


class HostCapabilities:
    def __init__(self, cache_path: str | Path | None = None, *, rescan_hours: int = 24) -> None:
        self.cache_path = Path(cache_path) if cache_path else ROOT / "memory" / "host_capabilities.json"
        self.rescan_hours = rescan_hours
        self.detected: list[DetectedCapability] = []
        self.machine: dict[str, str] = {}
        self.scanned_at: str | None = None
        self._installed_names: set[str] = set()

    def load_or_scan(self) -> None:
        if self._load_cache():
            logging.info("Host capabilities loaded from cache (%d items)", len(self.detected))
            return
        self.scan()

    def scan(self) -> None:
        self.machine = self._detect_machine()
        self._installed_names = self._collect_installed_names()
        audio_devices = self._scan_audio_devices()
        self.detected = []

        for key, signature in CAPABILITY_SIGNATURES.items():
            if not self._matches_signature(key, signature):
                continue

            matched_audio = [
                name for name in audio_devices
                if any(marker in name.lower() for marker in signature.get("audio_markers", []))
            ]
            if not matched_audio:
                for marker in signature.get("audio_markers", []):
                    matched_audio.extend(
                        name for name in audio_devices if marker in name.lower()
                    )
                matched_audio = list(dict.fromkeys(matched_audio))

            self.detected.append(
                DetectedCapability(
                    key=key,
                    display=signature["display"],
                    category=signature.get("category", "system"),
                    notes=signature.get("notes", ""),
                    launch_targets=[str(t) for t in signature.get("launch", [])],
                    audio_devices=matched_audio,
                )
            )

        self.scanned_at = datetime.now(timezone.utc).isoformat()
        self._save_cache()
        logging.info("Host scan complete — %d capabilities on %s", len(self.detected), self.machine.get("vendor", "PC"))

    def refresh(self) -> None:
        self.scan()

    def get(self, key: str) -> DetectedCapability | None:
        for item in self.detected:
            if item.key == key:
                return item
        return None

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def launch_target(self, name: str) -> str | None:
        lowered = name.lower().strip().replace("_", " ").replace("-", " ")
        for item in self.detected:
            if lowered in {item.key.replace("_", " "), item.display.lower()}:
                return item.launch_targets[0] if item.launch_targets else item.display
            if lowered in item.display.lower():
                return item.launch_targets[0] if item.launch_targets else item.display

        for key, signature in CAPABILITY_SIGNATURES.items():
            aliases = [key.replace("_", " "), signature["display"].lower(), *signature.get("markers", [])]
            if any(lowered in alias or alias in lowered for alias in aliases):
                launches = signature.get("launch", [])
                return str(launches[0]) if launches else signature["display"]
        return None

    def format_report(self) -> str:
        lines = [
            f"Host: {self.machine.get('vendor', 'Unknown')} {self.machine.get('model', '')}".strip(),
            f"CPU: {self.machine.get('cpu', 'Unknown')}",
            f"GPU: {self.machine.get('gpu', 'Unknown')}",
            f"Scanned: {self.scanned_at or 'not yet'}",
            "",
            f"Detected software ({len(self.detected)}):",
        ]
        if not self.detected:
            lines.append("  (none matched — Spine will use Windows defaults)")
        else:
            for item in self.detected:
                lines.append(f"  • {item.display} [{item.category}]")
                if item.audio_devices:
                    lines.append(f"    Audio: {', '.join(item.audio_devices)}")
                if item.notes:
                    lines.append(f"    {item.notes}")

        enhanced = find_enhanced_audio_devices()
        if enhanced["input"] or enhanced["output"]:
            lines.append("")
            lines.append("Enhanced audio endpoints:")
            for name in enhanced["input"]:
                lines.append(f"  Mic: {name}")
            for name in enhanced["output"]:
                lines.append(f"  Speaker: {name}")

        lines.append("")
        lines.append("Spine auto-uses noise-cancelling mics and wireless headsets when available.")
        lines.append("Say 'pc launch armoury crate' or 'open nvidia broadcast' to open detected tools.")
        return "\n".join(lines)

    def format_for_prompt(self) -> str:
        if not self.detected:
            return "This PC has no vendor-specific tools detected; use Windows built-in settings."

        lines = [
            f"Host machine: {self.machine.get('vendor', 'Unknown')} {self.machine.get('model', '')}".strip(),
            "Installed tools Spine can leverage on THIS computer:",
        ]
        for item in self.detected:
            detail = item.notes
            if item.audio_devices:
                detail += f" Active audio: {', '.join(item.audio_devices)}."
            lines.append(f"- {item.display}: {detail}")
        return "\n".join(lines)

    def _load_cache(self) -> bool:
        if not self.cache_path.exists():
            return False
        try:
            with self.cache_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return False

        scanned = data.get("scanned_at")
        if not scanned:
            return False

        try:
            scanned_dt = datetime.fromisoformat(scanned)
            age_hours = (datetime.now(timezone.utc) - scanned_dt).total_seconds() / 3600
            if age_hours > self.rescan_hours:
                return False
        except ValueError:
            return False

        self.machine = data.get("machine", {})
        self.scanned_at = scanned
        self.detected = [DetectedCapability(**item) for item in data.get("detected", [])]
        return True

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "scanned_at": self.scanned_at,
            "machine": self.machine,
            "detected": [asdict(item) for item in self.detected],
        }
        with self.cache_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def _detect_machine(self) -> dict[str, str]:
        info = {"vendor": "Unknown", "model": "", "cpu": "Unknown", "gpu": "Unknown"}
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    (
                        "$cs = Get-CimInstance Win32_ComputerSystem; "
                        "$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name; "
                        "$gpu = (Get-CimInstance Win32_VideoController | "
                        "Where-Object { $_.Name -notmatch 'Microsoft|Basic' } | "
                        "Select-Object -First 1).Name; "
                        "[pscustomobject]@{ Vendor=$cs.Manufacturer; Model=$cs.Model; "
                        "CPU=$cpu; GPU=$gpu } | ConvertTo-Json -Compress"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if result.stdout.strip():
                data = json.loads(result.stdout.strip())
                info["vendor"] = str(data.get("Vendor", "Unknown"))
                info["model"] = str(data.get("Model", ""))
                info["cpu"] = str(data.get("CPU", "Unknown"))
                info["gpu"] = str(data.get("GPU", "Unknown"))
        except Exception as exc:
            logging.debug("Machine detection failed: %s", exc)
        return info

    def _collect_installed_names(self) -> set[str]:
        names: set[str] = set()

        for hive, root in (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ):
            names.update(self._read_uninstall_key(hive, root))

        for path in (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        ):
            if path.exists():
                for child in path.iterdir():
                    if child.is_dir():
                        names.add(child.name.lower())

        return names

    def _read_uninstall_key(self, hive: int, root: str) -> set[str]:
        names: set[str] = set()
        try:
            with winreg.OpenKey(hive, root) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        sub_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_name) as sub:
                            display, _ = winreg.QueryValueEx(sub, "DisplayName")
                            if display:
                                names.add(str(display).lower())
                    except OSError:
                        continue
        except OSError:
            pass
        return names

    def _scan_audio_devices(self) -> list[str]:
        devices: list[str] = []
        for dev in sd.query_devices():
            if dev["max_input_channels"] > 0 or dev["max_output_channels"] > 0:
                devices.append(dev["name"])
        return devices

    def _matches_signature(self, key: str, signature: dict[str, Any]) -> bool:
        markers = [m.lower() for m in signature.get("markers", [])]
        if any(any(marker in name for marker in markers) for name in self._installed_names):
            return True

        for rel_path in signature.get("registry", []):
            if self._registry_exists(rel_path):
                return True

        for rel_path in signature.get("paths", []):
            if Path(rel_path).exists():
                return True

        return False

    def _registry_exists(self, rel_path: str) -> bool:
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, rel_path):
                    return True
            except OSError:
                continue
        return False


def _is_enhanced_audio_device(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in _ENHANCED_AUDIO_MARKERS)


def find_enhanced_audio_device(kind: str) -> int | None:
    """Prefer noise-cancelling / vendor-enhanced audio endpoints when present."""
    matches: list[tuple[int, int]] = []
    for i, dev in enumerate(sd.query_devices()):
        channels = dev["max_input_channels"] if kind == "input" else dev["max_output_channels"]
        if channels <= 0:
            continue
        if not _is_enhanced_audio_device(dev["name"]):
            continue
        score = 10
        lowered = dev["name"].lower()
        if "ai noise cancel" in lowered:
            score += 5
        if kind == "input" and "microphone" in lowered or "mic" in lowered or "input" in lowered:
            score += 2
        matches.append((score, i))

    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def find_enhanced_audio_devices() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"input": [], "output": []}
    for i, dev in enumerate(sd.query_devices()):
        name = dev["name"]
        if not _is_enhanced_audio_device(name):
            continue
        if dev["max_input_channels"] > 0:
            result["input"].append(name)
        if dev["max_output_channels"] > 0:
            result["output"].append(name)
    return result

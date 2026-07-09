"""Low-level Windows app control — launch, shell, focus, input."""

from __future__ import annotations

import logging
import os
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path


def run_powershell(script: str, *, timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_shell(command: str, *, timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def open_url(url: str) -> bool:
    try:
        webbrowser.open(url, new=1)
        return True
    except Exception as exc:
        logging.error("open_url failed: %s", exc)
        return False


def research_paper_urls(topic: str) -> list[str]:
    q = urllib.parse.quote_plus(topic.strip())
    return [
        f"https://scholar.google.com/scholar?q={q}",
        f"https://arxiv.org/search/?query={q}&searchtype=all",
        f"https://www.semanticscholar.org/search?q={q}",
    ]


def spotify_play(query: str) -> tuple[bool, str]:
    q = query.strip() or "top hits"
    uri = f"spotify:search:{urllib.parse.quote(q)}"
    try:
        os.startfile(uri)  # type: ignore[attr-defined]
        return True, q
    except OSError:
        pass

    candidates = [
        Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "Spotify.exe",
    ]
    for exe in candidates:
        if exe.exists():
            subprocess.Popen([str(exe), f"--uri={uri}"], shell=False)
            return True, q

    code, _, err = run_powershell(f'Start-Process "{uri}"')
    return code == 0, q if code == 0 else err


def find_start_app(name: str) -> str | None:
    needle = name.lower().replace("'", "''")
    script = f"""
$apps = Get-StartApps | Where-Object {{ $_.Name -like '*{needle}*' }}
if ($apps) {{ $apps[0].AppID }}
"""
    code, out, _ = run_powershell(script)
    if code == 0 and out:
        return out.splitlines()[0].strip()
    return None


def launch_app(name: str) -> tuple[bool, str]:
    target = name.strip().strip('"')
    if not target:
        return False, "No app name given."

    if target.lower().startswith(("http://", "https://")):
        return open_url(target), f"Opened {target}"

    # URI schemes (spotify:, ms-settings:, etc.)
    if ":" in target and not target.lower().endswith(".exe") and "\\" not in target:
        try:
            os.startfile(target)  # type: ignore[attr-defined]
            return True, f"Launched {target}"
        except OSError:
            pass

    path = Path(target)
    if path.exists():
        os.startfile(str(path))  # type: ignore[attr-defined]
        return True, f"Opened {path}"

    app_id = find_start_app(target)
    if app_id:
        code, _, err = run_powershell(f'explorer.exe shell:AppsFolder\\{app_id}!')
        if code == 0:
            return True, f"Launched {target}"
        run_powershell(f'Start-Process "shell:AppsFolder\\{app_id}!"')

    code, out, err = run_powershell(f'Start-Process "{target}"')
    if code == 0:
        return True, f"Launched {target}"

    code, where_out, _ = run_shell(f'where "{target}"')
    if code == 0 and where_out:
        exe = where_out.splitlines()[0]
        subprocess.Popen([exe], shell=False)
        return True, f"Launched {exe}"

    return False, err or f"Could not find or launch '{target}'."


def focus_window(title_fragment: str) -> tuple[bool, str]:
    frag = title_fragment.replace("'", "''")
    script = f"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win {{
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}}
"@
$p = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{frag}*' }} | Select-Object -First 1
if (-not $p) {{ exit 1 }}
[Win]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
[Win]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
$p.MainWindowTitle
"""
    code, out, err = run_powershell(script)
    if code == 0 and out:
        return True, f"Focused window: {out}"
    return False, err or f"No window matching '{title_fragment}'."


def send_keys(keys: str) -> tuple[bool, str]:
    escaped = keys.replace("'", "''")
    script = f"""
$w = New-Object -ComObject WScript.Shell
$w.SendKeys('{escaped}')
"""
    code, _, err = run_powershell(script)
    return code == 0, err or "Keys sent."


def list_windows() -> str:
    script = """
Get-Process | Where-Object { $_.MainWindowTitle } |
  Select-Object -First 25 ProcessName, MainWindowTitle |
  Format-Table -AutoSize | Out-String -Width 200
"""
    _, out, _ = run_powershell(script)
    return out or "No visible windows."


def kill_process(name: str) -> tuple[bool, str]:
    target = name.replace("'", "''")
    code, _, err = run_powershell(f"Stop-Process -Name '{target}' -Force -ErrorAction Stop")
    return code == 0, err or f"Stopped {name}."


def screen_size() -> tuple[int, int]:
    try:
        import pyautogui

        return pyautogui.size()
    except Exception:
        return 1920, 1080


def screen_click(x: int, y: int, *, button: str = "left") -> tuple[bool, str]:
    try:
        import pyautogui

        pyautogui.click(x=int(x), y=int(y), button=button)
        return True, f"Clicked ({x}, {y})."
    except Exception as exc:
        return False, str(exc)


def screen_move(x: int, y: int) -> tuple[bool, str]:
    try:
        import pyautogui

        pyautogui.moveTo(int(x), int(y))
        return True, f"Moved cursor to ({x}, {y})."
    except Exception as exc:
        return False, str(exc)


def screen_type_text(text: str) -> tuple[bool, str]:
    try:
        import pyautogui

        pyautogui.write(text, interval=0.02)
        return True, "Typed text."
    except Exception as exc:
        return False, str(exc)

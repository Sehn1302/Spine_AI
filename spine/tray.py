"""System tray icon for Spine."""

from __future__ import annotations

import logging
import threading
from typing import Callable

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None  # type: ignore


def _make_icon(size: int = 64) -> "Image.Image":
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(80, 160, 255, 255))
    draw.ellipse((16, 16, size - 16, size - 16), fill=(120, 200, 255, 200))
    return img


def run_tray(
    *,
    on_quit: Callable[[], None],
    on_restart_voice: Callable[[], None] | None = None,
    title: str = "Spine AI",
) -> threading.Thread | None:
    if pystray is None:
        logging.warning("pystray/Pillow not installed — tray icon disabled.")
        return None

    icon_image = _make_icon()

    def _quit(icon, _item) -> None:
        icon.stop()
        on_quit()

    def _restart(icon, _item) -> None:
        if on_restart_voice:
            on_restart_voice()

    menu = pystray.Menu(
        pystray.MenuItem("Spine — online", None, enabled=False),
        pystray.MenuItem("Restart voice", _restart) if on_restart_voice else None,
        pystray.MenuItem("Quit Spine", _quit),
    )
    menu = pystray.Menu(*(item for item in menu.items if item is not None))

    icon = pystray.Icon("spine", icon_image, title, menu)

    def _run() -> None:
        try:
            icon.run()
        except Exception as exc:
            logging.error("Tray icon failed: %s", exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread

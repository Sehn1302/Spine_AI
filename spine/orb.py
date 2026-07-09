"""Frameless particle sphere — small, vivid, transparent 3D orb."""

from __future__ import annotations

import math
import queue
import random
import tkinter as tk

from voice import SpineState

COLORS = ("#00e8ff", "#00b4d8", "#c77dff", "#e040fb", "#9d4edd", "#ff6bcb", "#48cae4")

STATE_PROFILE = {
    SpineState.SLEEPING: {"particles": 28, "radius": 0.42, "pulse": 0.03, "wave": 0.2, "brightness": 0.55, "speed": 0.5, "glow": 0.35},
    SpineState.IDLE: {"particles": 40, "radius": 0.44, "pulse": 0.04, "wave": 0.35, "brightness": 0.85, "speed": 1.0, "glow": 0.5},
    SpineState.LISTENING: {"particles": 52, "radius": 0.48, "pulse": 0.06, "wave": 0.55, "brightness": 1.0, "speed": 1.4, "glow": 0.7},
    SpineState.THINKING: {"particles": 56, "radius": 0.46, "pulse": 0.08, "wave": 0.8, "brightness": 1.0, "speed": 2.2, "glow": 0.75},
    SpineState.SPEAKING: {"particles": 54, "radius": 0.47, "pulse": 0.07, "wave": 0.65, "brightness": 1.0, "speed": 1.8, "glow": 0.7},
}

TRANSPARENT_KEY = "#010102"


def _blend_hex(hex_color: str, factor: float) -> str:
    factor = max(0.0, min(1.0, factor))
    r = int(int(hex_color[1:3], 16) * factor)
    g = int(int(hex_color[3:5], 16) * factor)
    b = int(int(hex_color[5:7], 16) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


class VisualOrb:
    def __init__(
        self,
        size: int = 48,
        title: str = "Spine",
        always_on_top: bool = True,
        position: str = "top-left",
    ) -> None:
        self.size = size
        self.title = title
        self.always_on_top = always_on_top
        self.position = position
        self.state = SpineState.SLEEPING
        self.state_queue: queue.Queue[SpineState] = queue.Queue()
        self.phase = 0.0
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self._drag_x = 0
        self._drag_y = 0
        self._particles = self._build_particles(72)
        self._scale = max(0.75, size / 48.0)

    def _build_particles(self, count: int) -> list[dict]:
        return [
            {
                "theta": random.uniform(0, math.tau),
                "phi": math.acos(random.uniform(-1, 1)),
                "offset": random.uniform(0, math.tau),
                "color": random.choice(COLORS),
                "size": random.uniform(1.0, 2.2),
            }
            for _ in range(count)
        ]

    def set_state(self, state: SpineState) -> None:
        self.state_queue.put(state)

    def _apply_state(self, state: SpineState) -> None:
        self.state = state
        if self.root:
            alpha = 0.88 if state == SpineState.SLEEPING else 1.0
            try:
                self.root.attributes("-alpha", alpha)
            except tk.TclError:
                pass

    def _draw_orb(self) -> None:
        if not self.canvas:
            return

        profile = STATE_PROFILE[self.state]
        self.canvas.delete("all")

        cx = cy = self.size // 2
        base_r = self.size * profile["radius"] * 0.5
        pulse = 1.0 + profile["pulse"] * math.sin(self.phase)
        radius = base_r * pulse
        brightness = profile["brightness"]
        glow = profile["glow"]
        count = profile["particles"]
        wave_strength = profile["wave"]

        # Soft core glow — keeps orb visible even when tiny
        for i, (color, alpha) in enumerate(
            (
                ("#00e8ff", glow * 0.25),
                ("#c77dff", glow * 0.18),
                ("#e040fb", glow * 0.12),
            )
        ):
            gr = radius * (1.15 - i * 0.12)
            fill = _blend_hex(color, alpha * brightness)
            self.canvas.create_oval(cx - gr, cy - gr, cx + gr, cy + gr, fill=fill, outline="")

        drawn: list[tuple[float, float, float, str, float]] = []
        for particle in self._particles[:count]:
            wave = wave_strength * math.sin(self.phase * profile["speed"] + particle["offset"])
            theta = particle["theta"] + wave * 0.4
            phi = particle["phi"] + wave * 0.2

            x3 = radius * math.sin(phi) * math.cos(theta)
            y3 = radius * math.sin(phi) * math.sin(theta)
            z3 = radius * math.cos(phi)

            depth = (z3 + radius) / (2 * radius) if radius else 0.5
            px = cx + x3
            py = cy + y3 * 0.88
            psize = max(1.1 * self._scale, particle["size"] * self._scale * (0.55 + depth * 0.65))
            color = _blend_hex(particle["color"], brightness * (0.45 + depth * 0.55))
            drawn.append((depth, px, py, color, psize))

        drawn.sort(key=lambda item: item[0])
        for _, px, py, color, psize in drawn:
            r = psize
            # Outer glow ring per particle
            glow_c = _blend_hex(color, 0.35)
            self.canvas.create_oval(px - r * 1.6, py - r * 1.6, px + r * 1.6, py + r * 1.6, fill=glow_c, outline="")
            self.canvas.create_oval(px - r, py - r, px + r, py + r, fill=color, outline="")

        self.phase += 0.06 * profile["speed"]

    def _poll(self) -> None:
        try:
            while True:
                self._apply_state(self.state_queue.get_nowait())
        except queue.Empty:
            pass

        self._draw_orb()
        if self.root:
            self.root.after(33, self._poll)

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event: tk.Event) -> None:
        if not self.root:
            return
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def run(self) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-transparentcolor", TRANSPARENT_KEY)
        self.root.attributes("-alpha", 0.92)
        if self.always_on_top:
            self.root.attributes("-topmost", True)

        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)

        self._apply_state(self.state)
        self._poll()
        self.root.update_idletasks()
        self._place_window()
        self.root.mainloop()

    def _place_window(self) -> None:
        if not self.root:
            return

        padding = 12
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        positions = {
            "top-left": (padding, padding),
            "top-right": (screen_w - self.size - padding, padding),
            "bottom-left": (padding, screen_h - self.size - padding),
            "bottom-right": (screen_w - self.size - padding, screen_h - self.size - padding),
        }
        x, y = positions.get(self.position, positions["top-left"])
        self.root.geometry(f"{self.size}x{self.size}+{x}+{y}")

    def stop(self) -> None:
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None

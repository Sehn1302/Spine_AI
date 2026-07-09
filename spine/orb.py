"""Frameless particle sphere — small, transparent, desktop-friendly."""

from __future__ import annotations

import math
import queue
import random
import tkinter as tk

from voice import SpineState

COLORS = ("#00e8ff", "#00b4d8", "#c77dff", "#e040fb", "#9d4edd")

STATE_PROFILE = {
    SpineState.SLEEPING: {"particles": 14, "radius": 0.38, "pulse": 0.01, "wave": 0.1, "brightness": 0.18, "speed": 0.3},
    SpineState.IDLE: {"particles": 36, "radius": 0.40, "pulse": 0.02, "wave": 0.3, "brightness": 0.7, "speed": 0.9},
    SpineState.LISTENING: {"particles": 44, "radius": 0.46, "pulse": 0.04, "wave": 0.5, "brightness": 1.0, "speed": 1.3},
    SpineState.THINKING: {"particles": 48, "radius": 0.42, "pulse": 0.06, "wave": 0.75, "brightness": 1.0, "speed": 2.0},
    SpineState.SPEAKING: {"particles": 46, "radius": 0.44, "pulse": 0.05, "wave": 0.6, "brightness": 1.0, "speed": 1.6},
}


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
        self._particles = self._build_particles(60)

    def _build_particles(self, count: int) -> list[dict]:
        return [
            {
                "theta": random.uniform(0, math.tau),
                "phi": math.acos(random.uniform(-1, 1)),
                "offset": random.uniform(0, math.tau),
                "color": random.choice(COLORS),
                "size": random.uniform(0.8, 1.6),
            }
            for _ in range(count)
        ]

    def set_state(self, state: SpineState) -> None:
        self.state_queue.put(state)

    def _apply_state(self, state: SpineState) -> None:
        self.state = state
        if self.root:
            alpha = 0.55 if state == SpineState.SLEEPING else 0.95
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
        base_r = self.size * profile["radius"]
        pulse = 1.0 + profile["pulse"] * 6 * abs(math.sin(self.phase))
        radius = base_r * pulse
        brightness = profile["brightness"]
        count = profile["particles"]
        wave_strength = profile["wave"]

        if brightness < 0.4:
            ring_r = radius + 2
            color = _blend_hex("#00e8ff", brightness * 0.4)
            self.canvas.create_oval(cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r, fill=color, outline="")

        drawn: list[tuple[float, float, str, float]] = []
        for particle in self._particles[:count]:
            wave = wave_strength * math.sin(self.phase * profile["speed"] + particle["offset"])
            theta = particle["theta"] + wave * 0.35
            phi = particle["phi"] + wave * 0.15

            x3 = radius * math.sin(phi) * math.cos(theta)
            y3 = radius * math.sin(phi) * math.sin(theta)
            z3 = radius * math.cos(phi)

            depth = (z3 + radius) / (2 * radius)
            px = cx + x3
            py = cy + y3 * 0.9
            psize = max(0.6, particle["size"] * (0.5 + depth * 0.6))
            color = _blend_hex(particle["color"], brightness * (0.3 + depth * 0.8))
            drawn.append((depth, px, py, color, psize))

        drawn.sort(key=lambda item: item[0])
        for _, px, py, color, psize in drawn:
            r = psize
            self.canvas.create_oval(px - r, py - r, px + r, py + r, fill=color, outline="")

        self.phase += 0.05 * profile["speed"]

    def _poll(self) -> None:
        try:
            while True:
                self._apply_state(self.state_queue.get_nowait())
        except queue.Empty:
            pass

        self._draw_orb()
        if self.root:
            self.root.after(40, self._poll)

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
        self.root.attributes("-transparentcolor", "#010101")
        self.root.attributes("-alpha", 0.55)
        if self.always_on_top:
            self.root.attributes("-topmost", True)

        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg="#010101",
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

"""Frameless particle sphere — clean AI visualization for Spine."""

from __future__ import annotations

import math
import queue
import random
import tkinter as tk

from voice import SpineState

# Reference palette: cyan, magenta, purple neon
COLORS = ("#00e8ff", "#00b4d8", "#c77dff", "#e040fb", "#9d4edd", "#7b2cbf")

STATE_PROFILE = {
    SpineState.SLEEPING: {
        "particles": 90,
        "radius": 0.34,
        "pulse": 0.012,
        "wave": 0.15,
        "brightness": 0.22,
        "speed": 0.4,
    },
    SpineState.IDLE: {
        "particles": 280,
        "radius": 0.38,
        "pulse": 0.02,
        "wave": 0.35,
        "brightness": 0.75,
        "speed": 1.0,
    },
    SpineState.LISTENING: {
        "particles": 340,
        "radius": 0.44,
        "pulse": 0.045,
        "wave": 0.55,
        "brightness": 1.0,
        "speed": 1.4,
    },
    SpineState.THINKING: {
        "particles": 380,
        "radius": 0.40,
        "pulse": 0.07,
        "wave": 0.85,
        "brightness": 1.0,
        "speed": 2.2,
    },
    SpineState.SPEAKING: {
        "particles": 360,
        "radius": 0.42,
        "pulse": 0.055,
        "wave": 0.7,
        "brightness": 1.0,
        "speed": 1.8,
    },
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
        size: int = 300,
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
        self._particles = self._build_particles(400)

    def _build_particles(self, count: int) -> list[dict]:
        items = []
        for _ in range(count):
            items.append(
                {
                    "theta": random.uniform(0, math.tau),
                    "phi": math.acos(random.uniform(-1, 1)),
                    "offset": random.uniform(0, math.tau),
                    "color": random.choice(COLORS),
                    "size": random.uniform(1.2, 2.8),
                }
            )
        return items

    def set_state(self, state: SpineState) -> None:
        self.state_queue.put(state)

    def _apply_state(self, state: SpineState) -> None:
        self.state = state

    def _draw_orb(self) -> None:
        if not self.canvas:
            return

        profile = STATE_PROFILE[self.state]
        self.canvas.delete("all")

        cx = cy = self.size // 2
        base_r = self.size * profile["radius"]
        pulse = 1.0 + profile["pulse"] * 8 * abs(math.sin(self.phase))
        radius = base_r * pulse
        brightness = profile["brightness"]
        count = profile["particles"]
        wave_strength = profile["wave"]

        # Soft outer halo
        halo_r = radius + 28
        for i, factor in enumerate((0.08, 0.05, 0.03)):
            r = halo_r - i * 8
            color = _blend_hex("#00e8ff", brightness * factor * 3)
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")

        # Particle sphere
        drawn: list[tuple[float, float, str, float]] = []
        for particle in self._particles[:count]:
            wave = wave_strength * math.sin(self.phase * profile["speed"] + particle["offset"])
            theta = particle["theta"] + wave * 0.4
            phi = particle["phi"] + wave * 0.2

            x3 = radius * math.sin(phi) * math.cos(theta)
            y3 = radius * math.sin(phi) * math.sin(theta)
            z3 = radius * math.cos(phi)

            depth = (z3 + radius) / (2 * radius)
            px = cx + x3
            py = cy + y3 * 0.92
            size = particle["size"] * (0.6 + depth * 0.9)
            color = _blend_hex(particle["color"], brightness * (0.35 + depth * 0.75))
            drawn.append((depth, px, py, color, size))

        drawn.sort(key=lambda item: item[0])
        for _, px, py, color, psize in drawn:
            r = psize
            self.canvas.create_oval(px - r, py - r, px + r, py + r, fill=color, outline="")

        # Inner energy waves (active states only)
        if brightness > 0.5:
            for ring in range(3):
                ring_r = radius * (0.35 + ring * 0.18)
                wave_offset = self.phase * profile["speed"] + ring
                points = []
                steps = 36
                for step in range(steps + 1):
                    angle = (step / steps) * math.tau
                    wobble = 1.0 + 0.08 * math.sin(angle * 4 + wave_offset)
                    rx = cx + math.cos(angle) * ring_r * wobble
                    ry = cy + math.sin(angle) * ring_r * wobble
                    points.extend([rx, ry])
                ring_color = _blend_hex("#e040fb" if ring % 2 else "#00e8ff", brightness * 0.25)
                if len(points) >= 4:
                    self.canvas.create_line(*points, fill=ring_color, smooth=True, width=1)

        self.phase += 0.04 * profile["speed"]

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
        self.root.attributes("-transparentcolor", "#010101")
        if self.always_on_top:
            self.root.attributes("-topmost", True)

        self.canvas = tk.Canvas(
            self.size,
            self.size,
            width=self.size,
            height=self.size,
            bg="#010101",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)

        self._poll()
        self.root.update_idletasks()
        self._place_window()
        self.root.mainloop()

    def _place_window(self) -> None:
        if not self.root:
            return

        padding = 20
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

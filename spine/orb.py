"""Animated orb UI — visual representation of Spine state."""

from __future__ import annotations

import queue
import tkinter as tk

from voice import SpineState


STATE_COLORS = {
    SpineState.SLEEPING: "#0d1520",
    SpineState.IDLE: "#1e3a5f",
    SpineState.LISTENING: "#2ecc71",
    SpineState.THINKING: "#f39c12",
    SpineState.SPEAKING: "#00d4ff",
}

STATE_GLOW = {
    SpineState.SLEEPING: "#1a2535",
    SpineState.IDLE: "#2d5a87",
    SpineState.LISTENING: "#58d68d",
    SpineState.THINKING: "#f5b041",
    SpineState.SPEAKING: "#5dade2",
}

STATE_SCALE = {
    SpineState.SLEEPING: 0.85,
    SpineState.IDLE: 1.0,
    SpineState.LISTENING: 1.18,
    SpineState.THINKING: 1.08,
    SpineState.SPEAKING: 1.12,
}

STATE_PULSE_SPEED = {
    SpineState.SLEEPING: 0.008,
    SpineState.IDLE: 0.015,
    SpineState.LISTENING: 0.04,
    SpineState.THINKING: 0.06,
    SpineState.SPEAKING: 0.05,
}


class VisualOrb:
    def __init__(
        self,
        size: int = 220,
        title: str = "Spine",
        always_on_top: bool = True,
        position: str = "top-left",
    ) -> None:
        self.size = size
        self.title = title
        self.always_on_top = always_on_top
        self.position = position
        self.state = SpineState.IDLE
        self.state_queue: queue.Queue[SpineState] = queue.Queue()
        self.pulse_phase = 0.0
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.status_label: tk.Label | None = None
        self._circle_ids: list[int] = []

    def set_state(self, state: SpineState) -> None:
        self.state_queue.put(state)

    def _apply_state(self, state: SpineState) -> None:
        self.state = state
        if self.status_label:
            labels = {
                SpineState.SLEEPING: "Sleeping — say 'Spine, wake up'",
                SpineState.IDLE: "Idle",
                SpineState.LISTENING: "Listening...",
                SpineState.THINKING: "Thinking...",
                SpineState.SPEAKING: "Speaking...",
            }
            self.status_label.config(text=labels[state])

    def _draw_orb(self) -> None:
        if not self.canvas:
            return

        self.canvas.delete("all")
        cx = self.size // 2
        cy = self.size // 2 - 10

        base_scale = STATE_SCALE[self.state]
        pulse = 1.0 + (STATE_PULSE_SPEED[self.state] * 10 * abs(__import__("math").sin(self.pulse_phase)))
        radius = int((self.size * 0.22) * base_scale * pulse)

        glow_radius = radius + 18
        self.canvas.create_oval(
            cx - glow_radius, cy - glow_radius,
            cx + glow_radius, cy + glow_radius,
            fill=STATE_GLOW[self.state], outline="",
        )
        self.canvas.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill=STATE_COLORS[self.state], outline="#ffffff", width=2,
        )
        self.canvas.create_text(cx, cy, text="S", fill="#ffffff", font=("Segoe UI", int(radius * 0.5), "bold"))

        self.pulse_phase += STATE_PULSE_SPEED[self.state]

    def _poll(self) -> None:
        try:
            while True:
                self._apply_state(self.state_queue.get_nowait())
        except queue.Empty:
            pass

        self._draw_orb()
        if self.root:
            self.root.after(40, self._poll)

    def run(self) -> None:
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.configure(bg="#0a0e17")
        self.root.resizable(False, False)
        if self.always_on_top:
            self.root.attributes("-topmost", True)

        frame = tk.Frame(self.root, bg="#0a0e17", padx=12, pady=12)
        frame.pack()

        self.canvas = tk.Canvas(
            frame, width=self.size, height=self.size - 20,
            bg="#0a0e17", highlightthickness=0,
        )
        self.canvas.pack()

        self.status_label = tk.Label(
            frame, text="Idle", fg="#8fa4bf", bg="#0a0e17",
            font=("Segoe UI", 10),
        )
        self.status_label.pack(pady=(4, 0))

        self._poll()
        self.root.update_idletasks()
        self._place_window()
        self.root.mainloop()

    def _place_window(self) -> None:
        if not self.root:
            return

        padding = 16
        win_w = self.root.winfo_reqwidth()
        win_h = self.root.winfo_reqheight()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        positions = {
            "top-left": (padding, padding),
            "top-right": (screen_w - win_w - padding, padding),
            "bottom-left": (padding, screen_h - win_h - padding),
            "bottom-right": (screen_w - win_w - padding, screen_h - win_h - padding),
        }
        x, y = positions.get(self.position, positions["top-left"])
        self.root.geometry(f"+{x}+{y}")

    def stop(self) -> None:
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None

"""Wispr Flow-style status pill: a small always-on-top capsule at the
bottom-center of the screen showing live mic levels while you speak,
a sweep animation while transcribing, and a brief result flash.

Never steals focus (WS_EX_NOACTIVATE) - the app you're dictating into
stays active the whole time.
"""

from __future__ import annotations

import collections
import tkinter as tk

from . import winutil

BG = "#17171f"
ACCENT = "#7c6cff"
OK = "#4ade80"
ERR = "#f87171"
TEXT = "#e6e6f0"
TRANSPARENT = "#000001"

W, H = 232, 52
N_BARS = 13
BAR_W = 5
BAR_GAP = 7


class Overlay:
    """States: hidden | listening | locked | processing | done | error."""

    def __init__(self, root: tk.Tk, level_source=None):
        self.root = root
        self.level_source = level_source or (lambda: 0.0)
        self.state = "hidden"
        self._levels = collections.deque([0.0] * N_BARS, maxlen=N_BARS)
        self._phase = 0
        self._hide_job = None

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", TRANSPARENT)
        self.win.configure(bg=TRANSPARENT)
        self.canvas = tk.Canvas(
            self.win, width=W, height=H, bg=TRANSPARENT,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack()
        self._place()
        self.win.withdraw()
        self.win.update_idletasks()
        try:
            hwnd = winutil.user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
            winutil.make_overlay_window(hwnd)
        except Exception:
            pass
        self._tick()

    def _place(self) -> None:
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x = (sw - W) // 2
        y = sh - H - 78  # sits just above the taskbar
        self.win.geometry(f"{W}x{H}+{x}+{y}")

    def set_state(self, state: str, message: str | None = None) -> None:
        self.state = state
        self.message = message
        if self._hide_job is not None:
            try:
                self.root.after_cancel(self._hide_job)
            except Exception:
                pass
            self._hide_job = None

        if state == "hidden":
            self.win.withdraw()
            return

        self._place()
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        if state in ("done", "error"):
            delay = 900 if state == "done" else 1400
            self._hide_job = self.root.after(delay, lambda: self.set_state("hidden"))

    # ------------------------------------------------------------- drawing

    def _pill(self) -> None:
        c = self.canvas
        r = H // 2
        c.create_oval(0, 0, H, H, fill=BG, outline=BG)
        c.create_oval(W - H, 0, W, H, fill=BG, outline=BG)
        c.create_rectangle(r, 0, W - r, H, fill=BG, outline=BG)

    def _draw_listening(self, color: str) -> None:
        level = 0.0
        try:
            level = float(self.level_source())
        except Exception:
            pass
        self._levels.append(min(1.0, level * 14.0))

        c = self.canvas
        total = N_BARS * BAR_W + (N_BARS - 1) * BAR_GAP
        x = (W - total) // 2
        mid = H // 2
        for i, lvl in enumerate(self._levels):
            h = max(3.0, lvl * (H - 22) / 1.0)
            c.create_rectangle(
                x, mid - h / 2, x + BAR_W, mid + h / 2,
                fill=color, outline=color,
            )
            x += BAR_W + BAR_GAP

    def _draw_processing(self) -> None:
        c = self.canvas
        n = 3
        cx = W // 2 - 24
        for i in range(n):
            active = (self._phase // 3) % n == i
            r = 5 if active else 3.5
            color = ACCENT if active else "#3a3a4a"
            x = cx + i * 24
            c.create_oval(x - r, H / 2 - r, x + r, H / 2 + r, fill=color, outline=color)

    def _draw_text(self, text: str, color: str) -> None:
        self.canvas.create_text(
            W // 2, H // 2, text=text, fill=color,
            font=("Segoe UI", 11, "bold"),
        )

    def _tick(self) -> None:
        try:
            if self.state != "hidden":
                self._phase += 1
                self.canvas.delete("all")
                self._pill()
                if self.state == "listening":
                    self._draw_listening(ACCENT)
                elif self.state == "locked":
                    self._draw_listening("#9d8fff")
                elif self.state == "processing":
                    self._draw_processing()
                elif self.state == "done":
                    self._draw_text("✓", OK)
                elif self.state == "error":
                    self._draw_text(self.message or "Didn't catch that", ERR)
                elif self.state == "loading":
                    self._draw_processing()
        except Exception:
            pass
        self.root.after(40, self._tick)

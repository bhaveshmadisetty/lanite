# overlay.py — Floating waveform HUD for Lanite
import ctypes
import logging
import math
import random
import time
import tkinter as tk
from typing import Callable

# ── Constants — Upgraded HTML Match ───────────────────────────────────────────
_TRANSPARENT = "#010101"    # colour used as chroma-key transparency
_BG          = "#12111a"    # Pill background
_BORDER      = "#2a2933"    # Subtle border
_ACCENT      = "#7c6ff7"    # Purple accent
_YELLOW      = "#f0c050"    # Processing yellow

_W, _H    = 460, 64
_RADIUS   = 22
_NUM_BARS = 16
_BAR_W    = 3
_BAR_GAP  = 3
_MARGIN_BOTTOM = 52


class Overlay:
    def __init__(self, root: tk.Tk, amplitude_getter: Callable[[], float]):
        self._root = root
        self._amp = amplitude_getter
        self._visible = False
        self._anim_id = None
        self._bar_ids: list = []
        self._bar_xs: list = []
        self._smoothed = [0.0] * _NUM_BARS
        self._click_through_applied = False
        
        # We need a small persistent history of volume to smooth it out
        self._vol_history = 0.0

        # ── Window ────────────────────────────────────────────────────────────
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.wm_attributes("-topmost", True)
        self._win.wm_attributes("-transparentcolor", _TRANSPARENT)
        self._win.configure(bg=_TRANSPARENT)
        self._win.withdraw()

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - _W) // 2
        y = sh - _H - _MARGIN_BOTTOM
        self._win.geometry(f"{_W}x{_H}+{x}+{y}")

        # ── Canvas ────────────────────────────────────────────────────────────
        self._cv = tk.Canvas(
            self._win, width=_W, height=_H,
            bg=_TRANSPARENT, highlightthickness=0,
        )
        self._cv.pack(fill="both", expand=True)

        self._draw_pill()
        self._draw_mic_badge()
        self._init_bars()
        self._draw_divider_and_close()
        self._draw_status_text()

    # ── Pill background ───────────────────────────────────────────────────────
    def _draw_pill(self):
        r = _RADIUS
        w, h = _W, _H
        kw = dict(fill=_BG, outline="", tags="pill")
        self._cv.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, **kw)
        self._cv.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, **kw)
        self._cv.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, **kw)
        self._cv.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, **kw)
        self._cv.create_rectangle(r, 0, w-r, h, **kw)
        self._cv.create_rectangle(0, r, w, h-r, **kw)
        
        # Border
        self._cv.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, outline=_BORDER, style="arc", tags="pill_border")
        self._cv.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, outline=_BORDER, style="arc", tags="pill_border")
        self._cv.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, outline=_BORDER, style="arc", tags="pill_border")
        self._cv.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, outline=_BORDER, style="arc", tags="pill_border")
        self._cv.create_line(r, 0, w-r, 0, fill=_BORDER, tags="pill_border")
        self._cv.create_line(r, h-1, w-r, h-1, fill=_BORDER, tags="pill_border")
        self._cv.create_line(0, r, 0, h-r, fill=_BORDER, tags="pill_border")
        self._cv.create_line(w-1, r, w-1, h-r, fill=_BORDER, tags="pill_border")

    def _draw_mic_badge(self):
        # Center of mic badge: x=18+15=33, y=32
        cx, cy = 33, _H // 2
        r = 15
        
        self._mic_bg = self._cv.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#1e1b30", outline="#282442", tags="mic_bg")
        
        # Draw SVG-like mic icon (using lines and arcs)
        # Scaled to fit roughly 10x14
        mx, my = cx, cy - 1
        mw, mh = 5, 8
        self._mic_fill = self._cv.create_rectangle(mx-mw/2, my-mh/2, mx+mw/2, my+mh/2, fill=_ACCENT, outline="", tags="mic_icon")
        self._mic_arc = self._cv.create_arc(mx-mw/2-2, my-mh/2, mx+mw/2+2, my+mh/2+3, start=180, extent=180, style="arc", outline=_ACCENT, width=1.4, tags="mic_icon")
        self._mic_stem = self._cv.create_line(mx, my+mh/2+3, mx, my+mh/2+6, fill=_ACCENT, width=1.4, tags="mic_icon")
        self._mic_base = self._cv.create_line(mx-3, my+mh/2+6, mx+3, my+mh/2+6, fill=_ACCENT, width=1.4, tags="mic_icon")

    def _init_bars(self):
        total_w = _NUM_BARS * _BAR_W + (_NUM_BARS - 1) * _BAR_GAP
        sx = (_W - total_w) // 2
        cy = _H // 2
        for i in range(_NUM_BARS):
            x = sx + i * (_BAR_W + _BAR_GAP)
            bid = self._cv.create_rectangle(
                x, cy - 1, x + _BAR_W, cy + 1,
                fill=_ACCENT, outline="", tags="bar"
            )
            self._bar_ids.append(bid)
            self._bar_xs.append(x)

    def _draw_divider_and_close(self):
        cx, cy = _W - 142, _H // 2
        self._cv.create_line(cx, cy - 12, cx, cy + 12, fill=_BORDER)
        
        # Close button (visual only)
        # 18px from right edge, center 22x22
        cls_x, cls_y = _W - 18 - 11, _H // 2
        cr = 11
        self._cv.create_oval(cls_x-cr, cls_y-cr, cls_x+cr, cls_y+cr, outline=_BORDER)
        self._cv.create_text(cls_x, cls_y-1, text="✕", font=("Segoe UI", 7), fill="#504e5d")

    def _draw_status_text(self):
        # Min width 88px, right aligned to the left of close btn padding
        tx = _W - 54
        
        self._lbl_status = self._cv.create_text(
            tx, _H // 2 - 6,
            text="Listening...",
            font=("Segoe UI Semibold", 9),
            fill="#a78bfa",
            anchor="e"
        )
        self._lbl_hint = self._cv.create_text(
            tx, _H // 2 + 8,
            text="Ctrl+Win to stop",
            font=("Segoe UI", 8),
            fill="#606070",
            anchor="e"
        )

    # ── Win32 click-through ───────────────────────────────────────────────────
    def _apply_click_through(self):
        if self._click_through_applied:
            return
        try:
            self._win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self._win.winfo_id())
            if not hwnd:
                hwnd = self._win.winfo_id()
            GWL_EXSTYLE      = -20
            WS_EX_LAYERED    = 0x00080000
            WS_EX_TRANSPARENT= 0x00000020
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000
            cur = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                cur | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            )
            self._click_through_applied = True
        except Exception as e:
            logging.warning(f"click-through failed: {e}")

    # ── Animation ─────────────────────────────────────────────────────────────
    def _animate(self, mode: str = "listening"):
        if not self._visible:
            return
        
        cy = _H // 2

        if mode == "listening":
            target_vol = self._amp()
            self._vol_history += (target_vol - self._vol_history) * 0.1
            vol = self._vol_history * 2.0  # Boost slightly for visual effect
            max_h = 26.0

            for i, (bid, bx) in enumerate(zip(self._bar_ids, self._bar_xs)):
                # Center weighting
                center = 1.0 - abs((i / (_NUM_BARS - 1)) - 0.5) * 1.3
                noise = 0.5 + random.random() * 0.5
                target = vol * center * noise * max_h
                
                self._smoothed[i] += (target - self._smoothed[i]) * 0.22
                bh = max(2.0, self._smoothed[i])
                
                # We can't do opacity easily on a per-element basis in Tkinter without complex
                # colour math, so we just stick to the accent color for simplicity.
                self._cv.coords(bid, bx, cy - bh / 2, bx + _BAR_W, cy + bh / 2)
                self._cv.itemconfig(bid, fill=_ACCENT)
                
            interval = 30
        
        else:
            # Processing symmetric ripple
            t = time.time()
            
            # Delay map: [0.00, 0.08, 0.16, 0.24, 0.32, 0.40, 0.48, 0.56, 0.48, 0.40, 0.32, 0.24, 0.16, 0.08, 0.00, 0.08]
            delays = []
            for i in range(8): delays.append(i * 0.08)
            for i in range(7, -1, -1): delays.append(i * 0.08)
            if len(delays) > 16: delays = delays[:16]

            # The animation repeats every 1.6s
            # At phase=0 -> h=2, phase=0.5 -> h=16, phase=1.0 -> h=2
            for i, (bid, bx) in enumerate(zip(self._bar_ids, self._bar_xs)):
                d = delays[i]
                phase = ((t - d) % 1.6) / 1.6
                
                # ease-in-out approximation for the pulse
                wave = math.sin(phase * math.pi)
                wave = wave * wave  # Make it a bit sharper at the peaks
                
                bh = 2.0 + (16.0 - 2.0) * wave
                self._cv.coords(bid, bx, cy - bh / 2, bx + _BAR_W, cy + bh / 2)
                self._cv.itemconfig(bid, fill=_YELLOW)
                
            interval = 30

        self._anim_id = self._win.after(interval, self._animate, mode)

    def _stop_anim(self):
        if self._anim_id:
            try:
                self._win.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

    # ── Public interface ──────────────────────────────────────────────────────
    def show_listening(self):
        self._visible = True
        self._stop_anim()
        self._cv.itemconfig(self._lbl_status, text="Listening...", fill="#a78bfa")
        self._cv.itemconfig(self._lbl_hint, text="Ctrl+Win to stop")
        
        self._cv.itemconfig(self._mic_bg, fill="#1e1b30", outline="#282442")
        self._cv.itemconfig(self._mic_fill, fill=_ACCENT)
        self._cv.itemconfig(self._mic_arc, outline=_ACCENT)
        self._cv.itemconfig(self._mic_stem, fill=_ACCENT)
        self._cv.itemconfig(self._mic_base, fill=_ACCENT)
        
        self._win.deiconify()
        self._win.wm_attributes("-topmost", True)
        self._win.lift()
        self._apply_click_through()
        self._animate("listening")

    def show_processing(self):
        self._stop_anim()
        self._cv.itemconfig(self._lbl_status, text="Processing...", fill=_YELLOW)
        self._cv.itemconfig(self._lbl_hint, text="Transcribing audio")
        
        self._cv.itemconfig(self._mic_bg, fill="#25211a", outline="#3b321e")
        self._cv.itemconfig(self._mic_fill, fill=_YELLOW)
        self._cv.itemconfig(self._mic_arc, outline=_YELLOW)
        self._cv.itemconfig(self._mic_stem, fill=_YELLOW)
        self._cv.itemconfig(self._mic_base, fill=_YELLOW)
        
        self._animate("processing")

    def hide(self):
        self._stop_anim()
        self._visible = False
        self._win.withdraw()

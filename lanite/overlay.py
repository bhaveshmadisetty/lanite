# overlay.py — Floating Dynamic-Island-style HUD for Lanite
"""
Rendering approach
------------------
Every frame is composited in PIL at 3x and downsampled with LANCZOS, then
handed to Tkinter as a single image.

The reason matters: Tkinter's canvas primitives (create_line, create_arc,
create_oval) have NO anti-aliasing. Drawing the waveform with them produces
hard, stair-stepped edges — bars that shimmer and crawl as their height
changes. That aliasing is what read as "cluttered" and "not smooth"; it isn't
a spacing problem, it's a rasterisation problem. Compositing the whole frame
in PIL gives genuinely smooth geometry at ~1.8ms/frame, comfortably inside a
60fps budget (measured; the 16.7ms budget is ~9x what we spend).

Motion
------
State changes are animated, not switched. The pill morphs between its two
widths on a spring curve with a little overshoot, while the contents
cross-fade. Nothing pops.
"""
import ctypes
import logging
import math
import random
import time
import tkinter as tk
from typing import Callable

# ── Palette ───────────────────────────────────────────────────────────────────
# Measured from the reference: the pill body is true #000 and the waveform
# averages ~#BCBCBC — not white. Neutrals carry a very slight blue bias so they
# read as chosen rather than default; luminance, not hue, is the accent here.
#
# Chroma key: Windows punches out EXACT matches only, so the key must (a) not
# equal any colour in the design, or parts of the HUD go transparent, and
# (b) not contrast with it, or the anti-aliased boundary survives as a coloured
# halo. A near-black grey satisfies both.
_TRANSPARENT = "#0a0a0a"
_BG          = "#000000"    # Pill body
_EDGE_HI     = "#23232a"    # Hairline specular highlight along the top edge
_BAR_HOT     = "#f4f4f8"    # Bar at full amplitude
_BAR_COOL    = "#8e8e99"    # Bar at rest
_DOT_DIM     = "#3a3a42"    # Static dots while processing
_ACCENT      = _BAR_HOT     # (compat alias)
_YELLOW      = "#f0c050"    # (compat alias, unused)

# ── Geometry ──────────────────────────────────────────────────────────────────
_H        = 44
_RADIUS   = _H // 2
_W_LISTEN = 158
_W_PROC   = 206
_PAD      = 8
_W        = _W_PROC + _PAD * 2
_H_CANVAS = _H + _PAD * 2
_CY       = _H_CANVAS / 2.0
_SS       = 3                      # Supersampling factor

# Waveform: thin, tightly pitched, rounded caps.
_NUM_BARS = 11
_BAR_W    = 3.0
_BAR_GAP  = 4.0
_BAR_MAX  = 19.0
_BAR_MIN  = 3.0

# Processing indicator
_DOT_R       = 1.7
_DOT_GAP     = 9.0
_NUM_DOTS    = 8
_SPIN_SPOKES = 8
_SPIN_R_IN   = 3.8
_SPIN_R_OUT  = 8.2
_SPIN_W      = 2.0

_MARGIN_BOTTOM = 56

# Motion timings (seconds)
#
# The container leads and the content follows: the pill starts moving
# immediately, while the cross-fade waits a beat (_FADE_DELAY) before starting.
# Swapping content while the shape is still travelling is what makes a morph
# feel cheap — letting the geometry commit first, then resolving the contents
# into it, is what reads as considered.
_MORPH_T    = 0.42                 # Pill width morph
_FADE_DELAY = 0.09                 # Content waits this long before fading
_FADE_T     = 0.22                 # Content cross-fade
_ENTER_T    = 0.34                 # Appear animation
_FPS_MS     = 16                   # ~60fps


def _hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t: float) -> tuple:
    """Blend two RGB tuples."""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def _ease_out_back(t: float, overshoot: float = 1.34) -> float:
    """
    Decelerating curve that overshoots slightly then settles.

    This is the 'bouncy' feel: the pill passes its target width by a couple of
    percent and eases back. Kept subtle — a big overshoot reads as a toy, a
    small one reads as physical.
    """
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    c1 = overshoot
    c3 = c1 + 1.0
    u = t - 1.0
    return 1.0 + c3 * u * u * u + c1 * u * u


def _ease_out_cubic(t: float) -> float:
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    u = 1.0 - t
    return 1.0 - u * u * u


class Overlay:
    def __init__(self, root: tk.Tk, amplitude_getter: Callable[[], float]):
        self._root = root
        self._amp = amplitude_getter
        self._visible = False
        self._anim_id = None
        self._click_through_applied = False
        self._hide_job = None

        self._smoothed = [0.0] * _NUM_BARS
        self._vol_history = 0.0

        # ── Animation state ───────────────────────────────────────────────
        # mode: what we're heading toward. Rendering interpolates toward it.
        self._mode = "listening"
        self._morph_from = _W_LISTEN     # Pill width at the start of a morph
        self._morph_to = _W_LISTEN
        self._morph_t0 = 0.0
        self._fade_t0 = 0.0              # Content cross-fade start
        self._enter_t0 = 0.0             # Appear animation start
        self._spin_phase = 0.0

        # ── Window ────────────────────────────────────────────────────────
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.wm_attributes("-topmost", True)
        self._win.wm_attributes("-transparentcolor", _TRANSPARENT)
        self._win.configure(bg=_TRANSPARENT)
        self._win.withdraw()

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - _W) // 2
        y = sh - _H_CANVAS - _MARGIN_BOTTOM
        self._win.geometry(f"{_W}x{_H_CANVAS}+{x}+{y}")

        self._cv = tk.Canvas(
            self._win, width=_W, height=_H_CANVAS,
            bg=_TRANSPARENT, highlightthickness=0,
        )
        self._cv.pack(fill="both", expand=True)

        self._photo = None
        self._img_item = self._cv.create_image(0, 0, anchor="nw")

    # ── Frame rendering ───────────────────────────────────────────────────
    def _render(self):
        """Composite one frame and push it to the canvas."""
        from PIL import Image, ImageDraw, ImageTk

        S = _SS
        now = time.perf_counter()

        # Pill width: spring toward the target.
        mt = (now - self._morph_t0) / _MORPH_T
        if mt >= 1.0:
            width = self._morph_to
        else:
            width = self._morph_from + (self._morph_to - self._morph_from) * _ease_out_back(mt)

        # Appear animation: scale up from 92% with a soft overshoot.
        et = (now - self._enter_t0) / _ENTER_T
        enter = _ease_out_back(et, 1.1) if et < 1.0 else 1.0
        scale = 0.92 + 0.08 * enter

        # Content cross-fade, held back so the container leads the content.
        ft = (now - self._fade_t0 - _FADE_DELAY) / _FADE_T
        ft = 1.0 if ft >= 1.0 else (0.0 if ft < 0 else ft)
        f = _ease_out_cubic(ft)
        wave_a = (1.0 - f) if self._mode == "processing" else f
        proc_a = f if self._mode == "processing" else (1.0 - f)

        img = Image.new("RGB", (_W * S, _H_CANVAS * S), _hex_rgb(_TRANSPARENT))
        mask = Image.new("L", (_W * S, _H_CANVAS * S), 0)
        d, md = ImageDraw.Draw(img), ImageDraw.Draw(mask)

        pw = width * scale
        ph = _H * scale
        x0 = (_W - pw) / 2.0 * S
        x1 = (_W + pw) / 2.0 * S
        y0 = (_CY - ph / 2.0) * S
        y1 = (_CY + ph / 2.0) * S
        r = min(ph / 2.0, _RADIUS) * S

        # Pill silhouette (coverage mask) + body.
        md.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=255)
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=_hex_rgb(_EDGE_HI))
        inset = max(1, S // 2)
        d.rounded_rectangle(
            [x0 + inset, y0 + inset * 2, x1 - inset, y1 + inset],
            radius=r, fill=_hex_rgb(_BG),
        )

        if wave_a > 0.01:
            self._draw_wave(d, S, wave_a)
        if proc_a > 0.01:
            self._draw_processing(d, S, proc_a, now)

        img = img.resize((_W, _H_CANVAS), Image.LANCZOS)
        mask = mask.resize((_W, _H_CANVAS), Image.LANCZOS)

        out = Image.new("RGB", (_W, _H_CANVAS), _hex_rgb(_TRANSPARENT))
        out.paste(img, (0, 0), mask)

        self._last_frame = out                 # exposed for design QA
        self._photo = ImageTk.PhotoImage(out)  # hold a ref; Tk won't
        self._cv.itemconfig(self._img_item, image=self._photo)
        return out

    def _draw_wave(self, d, S: int, alpha: float):
        """
        Listening: a symmetric row of rounded bars.

        Bars are drawn as rounded rectangles (not lines) so the caps stay
        perfectly circular at every height, and the whole row is alpha-blended
        toward the pill body so it can fade cleanly during a transition.
        """
        target_vol = self._amp()
        self._vol_history += (target_vol - self._vol_history) * 0.35
        vol = self._vol_history

        total_w = _NUM_BARS * _BAR_W + (_NUM_BARS - 1) * _BAR_GAP
        sx = (_W - total_w) / 2.0
        bg = _hex_rgb(_BG)

        for i in range(_NUM_BARS):
            # Symmetric weighting about the centre bar — a smooth cosine
            # envelope rather than a linear ramp, so the row reads as one
            # shape instead of eleven separate meters.
            p = (i / (_NUM_BARS - 1)) * 2.0 - 1.0     # -1 .. +1
            env = 0.45 + 0.55 * math.cos(p * math.pi / 2.0) ** 1.4
            jitter = 0.82 + random.random() * 0.18
            target = vol * env * jitter * _BAR_MAX

            k = 0.45 if target > self._smoothed[i] else 0.26
            self._smoothed[i] += (target - self._smoothed[i]) * k
            bh = max(_BAR_MIN, self._smoothed[i])

            lvl = min(1.0, (bh - _BAR_MIN) / max(1.0, _BAR_MAX - _BAR_MIN))
            col = _mix(_hex_rgb(_BAR_COOL), _hex_rgb(_BAR_HOT), lvl)
            col = _mix(bg, col, alpha)

            x = (sx + i * (_BAR_W + _BAR_GAP)) * S
            d.rounded_rectangle(
                [x, (_CY - bh / 2.0) * S, x + _BAR_W * S, (_CY + bh / 2.0) * S],
                radius=_BAR_W * S / 2.0, fill=col,
            )

    def _draw_processing(self, d, S: int, alpha: float, now: float):
        """
        Processing: a trail of dots leading into a rotating sunburst.

        The spinner advances on a continuous phase (not integer steps), and
        each spoke's brightness is a smooth function of its angular distance
        from the leading edge — so it sweeps rather than ticks.
        """
        bg = _hex_rgb(_BG)
        dots_w = (_NUM_DOTS - 1) * _DOT_GAP
        gap = 20.0
        group_w = dots_w + gap + _SPIN_R_OUT * 2
        dsx = (_W - group_w) / 2.0 + _DOT_R
        cx = dsx + dots_w + gap + _SPIN_R_OUT

        for i in range(_NUM_DOTS):
            # Gentle travelling shimmer along the dot row, so the left side
            # isn't visually dead while the spinner works.
            wave = 0.5 + 0.5 * math.sin(now * 3.0 - i * 0.45)
            col = _mix(bg, _mix(_hex_rgb(_DOT_DIM), _hex_rgb(_BAR_COOL), wave * 0.5), alpha)
            x = (dsx + i * _DOT_GAP) * S
            d.ellipse([x - _DOT_R * S, (_CY - _DOT_R) * S,
                       x + _DOT_R * S, (_CY + _DOT_R) * S], fill=col)

        phase = (now * 1.15) % 1.0        # ~1.15 rev/sec
        for i in range(_SPIN_SPOKES):
            frac = i / _SPIN_SPOKES
            ang = 2 * math.pi * frac - math.pi / 2
            # Angular distance behind the leading edge, 0..1
            rel = (frac - phase) % 1.0
            bright = (1.0 - rel) ** 1.6
            col = _mix(bg, _mix(_hex_rgb(_DOT_DIM), _hex_rgb(_BAR_HOT), bright), alpha)

            ca, sa = math.cos(ang), math.sin(ang)
            ax, ay = cx + ca * _SPIN_R_IN, _CY + sa * _SPIN_R_IN
            bx, by = cx + ca * _SPIN_R_OUT, _CY + sa * _SPIN_R_OUT
            d.line([ax * S, ay * S, bx * S, by * S],
                   fill=col, width=int(_SPIN_W * S))
            # Round the cap ends manually — ImageDraw.line has no capstyle.
            rr = _SPIN_W * S / 2.0
            for px, py in ((ax, ay), (bx, by)):
                d.ellipse([px * S - rr, py * S - rr, px * S + rr, py * S + rr],
                          fill=col)

    # ── Win32 click-through ───────────────────────────────────────────────
    def _apply_click_through(self):
        if self._click_through_applied:
            return
        try:
            self._win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self._win.winfo_id())
            if not hwnd:
                hwnd = self._win.winfo_id()
            GWL_EXSTYLE       = -20
            WS_EX_LAYERED     = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOOLWINDOW  = 0x00000080
            WS_EX_NOACTIVATE  = 0x08000000
            cur = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                cur | WS_EX_LAYERED | WS_EX_TRANSPARENT
                | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            )
            self._click_through_applied = True
        except Exception as e:
            logging.warning(f"click-through failed: {e}")

    # ── Animation loop ────────────────────────────────────────────────────
    def _animate(self, mode: str = None):
        """
        Single render loop for every state. `mode` is accepted for backward
        compatibility with older call sites but the loop reads self._mode.
        """
        if not self._visible:
            return
        try:
            self._render()
        except Exception as e:
            logging.debug(f"overlay render error: {e}")
        self._anim_id = self._win.after(_FPS_MS, self._animate)

    def _stop_anim(self):
        if self._anim_id:
            try:
                self._win.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

    def _start_morph(self, to_width: float):
        """Begin a spring morph from the current interpolated width."""
        now = time.perf_counter()
        mt = (now - self._morph_t0) / _MORPH_T
        if mt >= 1.0:
            cur = self._morph_to
        else:
            cur = self._morph_from + (self._morph_to - self._morph_from) * _ease_out_back(mt)
        self._morph_from = cur
        self._morph_to = to_width
        self._morph_t0 = now

    # ── Public interface ──────────────────────────────────────────────────
    def show_listening(self):
        self._cancel_hide_job()
        was_visible = self._visible
        self._visible = True

        self._vol_history = 0.0
        self._smoothed = [0.0] * _NUM_BARS

        now = time.perf_counter()
        if self._mode != "listening":
            self._fade_t0 = now
        self._mode = "listening"
        self._start_morph(_W_LISTEN)

        if not was_visible:
            # Fresh appearance: play the enter animation and skip the morph
            # so it doesn't grow from the previous session's width.
            self._enter_t0 = now
            self._fade_t0 = now - _FADE_T - _FADE_DELAY   # already fully faded
            self._morph_from = self._morph_to = _W_LISTEN
            self._morph_t0 = now - _MORPH_T

        self._win.deiconify()
        self._win.wm_attributes("-topmost", True)
        self._win.lift()
        self._apply_click_through()
        self._stop_anim()
        self._animate()

    def show_processing(self):
        self._cancel_hide_job()
        now = time.perf_counter()
        if self._mode != "processing":
            self._fade_t0 = now
        self._mode = "processing"
        self._start_morph(_W_PROC)

        if not self._visible:
            self._visible = True
            self._enter_t0 = now
            self._win.deiconify()
            self._win.wm_attributes("-topmost", True)
            self._win.lift()
            self._apply_click_through()

        self._stop_anim()
        self._animate()

    def show_loading(self):
        """
        Shown when the hotkey is pressed before the Whisper model has finished
        loading. Nothing else dismisses this (no recording started), so it
        self-hides after a short beat. Repeated calls must not stack timers.
        """
        self._cancel_hide_job()
        self.show_processing()
        self._hide_job = self._win.after(1600, self.hide)

    def _cancel_hide_job(self):
        if self._hide_job:
            try:
                self._win.after_cancel(self._hide_job)
            except Exception:
                pass
            self._hide_job = None

    def hide(self):
        self._cancel_hide_job()
        self._stop_anim()
        self._visible = False
        self._win.withdraw()

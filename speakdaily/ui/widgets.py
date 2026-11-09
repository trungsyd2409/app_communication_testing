"""Small reusable widgets."""
from __future__ import annotations

import math
import tkinter as tk

import customtkinter as ctk

from .. import theme as t


def card(parent, **kw) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=t.SURFACE, corner_radius=16,
                        border_width=1, border_color=t.BORDER, **kw)


def label(parent, text="", size=14, weight="normal", color=t.INK, **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=t.font(size, weight), text_color=color,
                        anchor=kw.pop("anchor", "w"), justify=kw.pop("justify", "left"), **kw)


def button(parent, text, command=None, kind="primary", icon_name=None, size="md", **kw):
    """kind: primary (terracotta), teal, neutral, ghost."""
    styles = {
        "primary": (t.ACCENT, t.ACCENT_HOVER, t.WHITE, t.WHITE),
        "teal": (t.TEAL, t.TEAL_HOVER, t.WHITE, t.WHITE),
        "neutral": (t.NEUTRAL_BTN, t.NEUTRAL_HOVER, t.INK, t.INK),
        "ghost": ("transparent", t.NEUTRAL_BTN, t.INK, t.INK),
    }
    fg, hover, text_color, icon_color = styles[kind]
    heights = {"sm": 32, "md": 42, "lg": 64}
    fonts = {"sm": t.font(13), "md": t.font(14, "bold"), "lg": t.font(20, "bold")}
    icon_px = {"sm": 16, "md": 18, "lg": 28}[size]
    image = t.icon(icon_name, icon_px, icon_color) if icon_name else None
    return ctk.CTkButton(parent, text=text, command=command, image=image, compound="left",
                         fg_color=fg, hover_color=hover, text_color=text_color,
                         font=fonts[size], height=kw.pop("height", heights[size]),
                         corner_radius=kw.pop("corner_radius", 12 if size != "lg" else 18),
                         **kw)


def icon_button(parent, icon_name, command=None, tooltip_text="", color=t.INK, size=18):
    btn = ctk.CTkButton(parent, text="", image=t.icon(icon_name, size, color), width=36, height=36,
                        fg_color="transparent", hover_color=t.NEUTRAL_BTN, corner_radius=10,
                        command=command)
    if tooltip_text:
        Tooltip(btn, tooltip_text)
    return btn


def segmented(parent, values, command=None, variable=None, height=36):
    return ctk.CTkSegmentedButton(
        parent, values=values, command=command, variable=variable, height=height,
        font=t.font(13, "bold"), corner_radius=10,
        selected_color=t.TEAL_SOFT, selected_hover_color=t.TEAL_SOFT,
        unselected_color=t.NEUTRAL_BTN, unselected_hover_color=t.NEUTRAL_HOVER,
        fg_color=t.NEUTRAL_BTN, text_color=t.INK)


def checkbox(parent, text, variable, command=None):
    return ctk.CTkCheckBox(parent, text=text, variable=variable, command=command,
                           font=t.font(13), text_color=t.INK, fg_color=t.TEAL,
                           hover_color=t.TEAL_HOVER, border_color=t.MUTED, checkmark_color=t.WHITE,
                           corner_radius=6, border_width=2)


def scroll_frame(parent, **kw):
    return ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                  scrollbar_button_color=t.BORDER,
                                  scrollbar_button_hover_color=t.MUTED, **kw)


def chip(parent, text, icon_name=None, selected=False, command=None, color="accent"):
    soft, strong = (t.ACCENT_SOFT, t.ACCENT) if color == "accent" else (t.TEAL_SOFT, t.TEAL)
    return ctk.CTkButton(
        parent, text=text, command=command, height=32, corner_radius=16,
        image=t.icon(icon_name, 16, strong if selected else t.MUTED) if icon_name else None,
        compound="left", font=t.font(13, "bold" if selected else "normal"),
        fg_color=soft if selected else t.SURFACE, hover_color=soft,
        text_color=strong if selected else t.INK,
        border_width=1, border_color=strong if selected else t.BORDER,
    )


def tag(parent, text, color="teal"):
    soft, strong = (t.TEAL_SOFT, t.TEAL) if color == "teal" else (t.ACCENT_SOFT, t.ACCENT)
    if color == "muted":
        soft, strong = t.NEUTRAL_BTN, t.MUTED
    return ctk.CTkLabel(parent, text=f"  {text}  ", fg_color=soft, text_color=strong,
                        corner_radius=10, font=t.font(12, "bold"), height=24)


class FlowFrame(ctk.CTkFrame):
    """Lays children out left to right and wraps to the next line."""

    def __init__(self, parent, gap=8, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self.gap = gap
        self._items: list = []
        self.bind("<Configure>", lambda e: self._relayout(e.width))

    def add(self, widget):
        self._items.append(widget)
        self.after_idle(lambda: self._relayout(self.winfo_width()))
        return widget

    def clear(self):
        for w in self._items:
            w.destroy()
        self._items = []

    def _relayout(self, width):
        if width <= 1:
            width = 600
        scaling = ctk.ScalingTracker.get_widget_scaling(self)
        gap = self.gap * scaling
        x = y = 0
        row_h = 0
        for w in self._items:
            ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
            if x > 0 and x + ww > width:
                x = 0
                y += row_h + gap
                row_h = 0
            w.place(x=x / scaling, y=y / scaling)
            x += ww + gap
            row_h = max(row_h, wh)
        total = y + row_h
        new_h = max(1, int(total / scaling))
        if getattr(self, "_last_h", None) != new_h:
            self._last_h = new_h
            self.configure(height=new_h)


class TimerRing(tk.Canvas):
    """Circular countdown."""

    def __init__(self, parent, size=260):
        super().__init__(parent, width=size, height=size, highlightthickness=0, bd=0)
        self.size = size
        self.fraction = 1.0
        self.big = "00:00"
        self.small = ""
        self.color = t.ACCENT
        self.redraw()

    def set(self, fraction, big, small="", color=None):
        self.fraction = max(0.0, min(1.0, fraction))
        self.big, self.small = big, small
        if color:
            self.color = color
        self.redraw()

    def redraw(self):
        self.delete("all")
        s, pad, width = self.size, 18, 16
        self.configure(bg=t.mode_color(t.SURFACE))
        box = (pad, pad, s - pad, s - pad)
        self.create_oval(*box, outline=t.mode_color(t.NEUTRAL_BTN), width=width)
        if self.fraction > 0:
            extent = -359.9 * self.fraction
            self.create_arc(*box, start=90, extent=extent, style="arc",
                            outline=t.mode_color(self.color), width=width)
            # round cap at the moving end
            angle = math.radians(90 + extent)
            r = (s - 2 * pad) / 2
            cx = s / 2 + r * math.cos(angle)
            cy = s / 2 - r * math.sin(angle)
            self.create_oval(cx - width / 2, cy - width / 2, cx + width / 2, cy + width / 2,
                             fill=t.mode_color(self.color), outline="")
            self.create_oval(s / 2 - width / 2, pad - width / 2, s / 2 + width / 2,
                             pad + width / 2, fill=t.mode_color(self.color), outline="")
        self.create_text(s / 2, s / 2 - 8, text=self.big, fill=t.mode_color(t.INK),
                         font=(t.FONT, 44, "bold"))
        self.create_text(s / 2, s / 2 + 34, text=self.small, fill=t.mode_color(t.MUTED),
                         font=(t.FONT, 13))


class BarChart(tk.Canvas):
    """Minutes spoken per day."""

    def __init__(self, parent, data, height=170):
        super().__init__(parent, height=height, highlightthickness=0, bd=0)
        self.data = data
        self.h = height
        self.bind("<Configure>", lambda e: self.redraw(e.width))

    def redraw(self, width):
        self.delete("all")
        self.configure(bg=t.mode_color(t.SURFACE))
        if not self.data:
            return
        n = len(self.data)
        top, bottom, left = 22, 28, 8
        slot = (width - 2 * left) / n
        bar_w = min(28, slot * 0.6)
        peak = max([m for _, m in self.data] + [5])
        for i, (day, minutes) in enumerate(self.data):
            x = left + slot * i + slot / 2
            bar_h = (self.h - top - bottom) * (minutes / peak)
            y0 = self.h - bottom - max(bar_h, 2)
            color = t.ACCENT if i == n - 1 else t.TEAL
            self.create_rectangle(x - bar_w / 2, y0, x + bar_w / 2, self.h - bottom,
                                  fill=t.mode_color(color if minutes else t.NEUTRAL_BTN),
                                  outline="")
            if minutes:
                self.create_text(x, y0 - 10, text=f"{minutes:.0f}",
                                 fill=t.mode_color(t.MUTED), font=(t.FONT, 9))
            self.create_text(x, self.h - bottom + 14, text=day.strftime("%d"),
                             fill=t.mode_color(t.MUTED), font=(t.FONT, 9))


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="#2B2A28", fg="#F6F1E7",
                 font=(t.FONT, 10), padx=8, pady=4).pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


def wrap_on_resize(lbl: ctk.CTkLabel, margin=40):
    """Keep a label's text wrapped to its parent width."""
    parent = lbl.master

    def update(event):
        scaling = ctk.ScalingTracker.get_widget_scaling(lbl)
        lbl.configure(wraplength=max(200, int(event.width / scaling) - margin))
    parent.bind("<Configure>", update, add="+")


def readonly_text(parent, text, height=160):
    box = ctk.CTkTextbox(parent, height=height, wrap="word", font=t.font(14),
                         fg_color=t.BG, text_color=t.INK, border_width=0, corner_radius=12)
    box.insert("1.0", text or "No reference answer yet. Add one in the Library or your Google Sheet.")
    box.configure(state="disabled")
    return box


def fmt_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def fmt_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    m, s = divmod(seconds, 60)
    if m and s:
        return f"{m}m {s}s"
    return f"{m} min" if m else f"{s}s"

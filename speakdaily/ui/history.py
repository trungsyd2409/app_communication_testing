"""Progress: totals, a 14-day chart and recent sessions."""
from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from .. import audio, paths
from .. import theme as t
from . import widgets as w

RATING_TEXT = {1: "Struggled", 2: "Hard", 3: "OK", 4: "Good", 5: "Easy"}


class HistoryScreen(ctk.CTkScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent", scrollbar_button_color=t.BORDER,
                         scrollbar_button_hover_color=t.MUTED)
        self.app = app
        self.store = app.store
        self.player = audio.Player()
        self.columnconfigure(0, weight=1)
        stats = self.store.stats()

        w.label(self, "History", 28, "bold").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 14))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=4)
        cards = [
            ("clock", "Total time", w.fmt_duration(stats["total_minutes"] * 60)),
            ("mic", "Sessions", str(stats["sessions"])),
            ("flame", "Streak", f"{stats['streak']} day" + ("" if stats["streak"] == 1 else "s")),
            ("star", "Average rating",
             f"{stats['avg_rating']:.1f} / 5" if stats["avg_rating"] else "No ratings"),
        ]
        for i, (icon_name, title, value) in enumerate(cards):
            row.columnconfigure(i, weight=1, uniform="s")
            box = w.card(row)
            box.grid(row=0, column=i, sticky="ew", padx=4)
            ctk.CTkLabel(box, text="", image=t.icon(icon_name, 20, t.ACCENT)).grid(
                row=0, column=0, rowspan=2, padx=(16, 10), pady=14)
            w.label(box, title, 12, color=t.MUTED).grid(row=0, column=1, sticky="sw", pady=(12, 0))
            w.label(box, value, 18, "bold").grid(row=1, column=1, sticky="nw", pady=(0, 12))

        chart_card = w.card(self)
        chart_card.grid(row=2, column=0, sticky="ew", padx=8, pady=(14, 0))
        chart_card.columnconfigure(0, weight=1)
        w.label(chart_card, "Minutes spoken, last 14 days", 15, "bold").grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 4))
        w.BarChart(chart_card, stats["last_14"]).grid(row=1, column=0, sticky="ew",
                                                      padx=16, pady=(0, 14))

        w.label(self, "Recent sessions", 16, "bold").grid(row=3, column=0, sticky="w",
                                                          padx=10, pady=(20, 6))
        recent = list(reversed(self.store.history))[:40]
        if not recent:
            w.label(self, "No sessions yet. Your practice will show up here.", 14,
                    color=t.MUTED).grid(row=4, column=0, sticky="w", padx=10)
        for i, entry in enumerate(recent):
            self._entry(4 + i, entry)

    def _entry(self, r, entry):
        box = w.card(self)
        box.grid(row=r, column=0, sticky="ew", padx=8, pady=3)
        box.columnconfigure(1, weight=1)
        try:
            when = datetime.fromisoformat(entry["finished_at"]).strftime("%a %d %b, %H:%M")
        except (KeyError, ValueError):
            when = ""
        ctk.CTkLabel(box, text="", image=t.icon(t.topic_icon(entry.get("topic", "")), 18,
                                                 t.TEAL)).grid(row=0, column=0, rowspan=2,
                                                               padx=(14, 10), pady=10)
        text = entry.get("question", "")
        w.label(box, text if len(text) < 110 else text[:107] + "...", 13, "bold").grid(
            row=0, column=1, sticky="w", pady=(10, 0))
        rating = entry.get("rating")
        meta = (f"{when}   ·   {w.fmt_duration(entry.get('spoken_seconds', 0))} of "
                f"{w.fmt_duration(entry.get('planned_seconds', 0))}"
                + (f"   ·   {RATING_TEXT.get(rating, '')}" if rating else ""))
        if entry.get("note"):
            meta += f"   ·   Note: {entry['note']}"
        w.label(box, meta, 12, color=t.MUTED).grid(row=1, column=1, sticky="w", pady=(2, 10))
        path = paths.recordings_dir() / entry["recording"] if entry.get("recording") else None
        if path and path.exists():
            w.icon_button(box, "play", lambda p=path: self.play(p), "Play recording",
                          t.ACCENT).grid(row=0, column=2, rowspan=2, padx=10)

    def play(self, path):
        if self.player.playing:
            self.player.stop()
        elif not self.player.play(path):
            self.app.toast(self.player.error)

    def destroy(self):
        self.player.stop()
        super().destroy()

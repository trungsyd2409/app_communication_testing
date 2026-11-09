"""Practice flow: home -> session (question + timer + recording) -> review."""
from __future__ import annotations

import time
from datetime import datetime

import customtkinter as ctk

from .. import audio, paths, picker
from .. import theme as t
from ..storage import Question
from . import widgets as w

RATINGS = [(1, "Struggled"), (2, "Hard"), (3, "OK"), (4, "Good"), (5, "Easy")]


def greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


# ======================================================================== HOME
class HomeScreen(ctk.CTkScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent", scrollbar_button_color=t.BORDER,
                         scrollbar_button_hover_color=t.MUTED)
        self.app = app
        self.store = app.store
        self.columnconfigure(0, weight=1)

        w.label(self, f"{greeting()}. Ready to speak?", 30, "bold").grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        w.label(self, "Press Start to get a random question and a random time "
                      "between 1 and 10 minutes.", 15, color=t.MUTED).grid(
            row=1, column=0, sticky="w", padx=8, pady=(0, 18))

        # stats ------------------------------------------------------------
        stats = self.store.stats()
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=4)
        for i in range(3):
            row.columnconfigure(i, weight=1, uniform="stat")
        self._stat(row, 0, "clock", "Today", w.fmt_duration(stats["today_minutes"] * 60))
        self._stat(row, 1, "flame", "Streak",
                   f"{stats['streak']} day" + ("" if stats["streak"] == 1 else "s"))
        self._stat(row, 2, "library", "Questions", str(len(self.store.questions)))

        # topics -----------------------------------------------------------
        box = w.card(self)
        box.grid(row=3, column=0, sticky="ew", padx=8, pady=(18, 0))
        box.columnconfigure(0, weight=1)
        w.label(box, "Topics", 16, "bold").grid(row=0, column=0, sticky="w", padx=20, pady=(16, 2))
        w.label(box, "Pick the topics for today. Nothing selected means all topics.", 13,
                color=t.MUTED).grid(row=1, column=0, sticky="w", padx=20)
        self.flow = w.FlowFrame(box)
        self.flow.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 18))
        self.selected = {tp for tp in self.store.settings.get("selected_topics", [])
                         if tp in self.store.topics()}
        self._draw_topics()

        # time mode ----------------------------------------------------------
        box2 = w.card(self)
        box2.grid(row=4, column=0, sticky="ew", padx=8, pady=(14, 0))
        box2.columnconfigure(1, weight=1)
        w.label(box2, "Time", 16, "bold").grid(row=0, column=0, sticky="w", padx=20, pady=16)
        self.mode = ctk.StringVar(value="Random 1–10 min" if self.store.settings.get(
            "time_mode") != "quick" else "Quick 1–3 min")
        seg = w.segmented(box2, ["Random 1–10 min", "Quick 1–3 min"],
                          command=self._mode_changed, variable=self.mode)
        seg.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=16)

        # start --------------------------------------------------------------
        start = w.button(self, "  Start speaking", self.start, kind="primary",
                         icon_name="mic", size="lg")
        start.grid(row=5, column=0, sticky="ew", padx=8, pady=(22, 10))

        # sync status ----------------------------------------------------------
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=6, column=0, sticky="ew", padx=8, pady=(6, 10))
        foot.columnconfigure(1, weight=1)
        has_sheet = bool(self.store.settings.get("sheet_url"))
        ctk.CTkLabel(foot, text="", image=t.icon("cloud" if has_sheet else "cloud-off", 18,
                                                  t.MUTED)).grid(row=0, column=0, padx=(4, 8))
        self.sync_label = w.label(foot, app.sync_status_text(), 13, color=t.MUTED)
        self.sync_label.grid(row=0, column=1, sticky="w")
        if has_sheet:
            w.button(foot, "Sync now", app.sync_now, kind="ghost", icon_name="refresh-cw",
                     size="sm", width=110).grid(row=0, column=2)
        else:
            w.button(foot, "Connect Google Sheet", lambda: app.show("settings"), kind="ghost",
                     icon_name="settings", size="sm").grid(row=0, column=2)

    def _stat(self, parent, col, icon_name, title, value):
        box = w.card(parent)
        box.grid(row=0, column=col, sticky="ew", padx=4)
        ctk.CTkLabel(box, text="", image=t.icon(icon_name, 22, t.ACCENT)).grid(
            row=0, column=0, rowspan=2, padx=(18, 12), pady=16)
        w.label(box, title, 13, color=t.MUTED).grid(row=0, column=1, sticky="sw", pady=(14, 0))
        w.label(box, value, 20, "bold").grid(row=1, column=1, sticky="nw", pady=(0, 14))

    def _draw_topics(self):
        self.flow.clear()
        self.flow.add(w.chip(self.flow, "All topics", "shuffle", selected=not self.selected,
                             command=self._select_all))
        for topic in self.store.topics():
            self.flow.add(w.chip(self.flow, topic, t.topic_icon(topic),
                                 selected=topic in self.selected,
                                 command=lambda tp=topic: self._toggle(tp)))

    def _toggle(self, topic):
        self.selected ^= {topic}
        self._save_topics()

    def _select_all(self):
        self.selected = set()
        self._save_topics()

    def _save_topics(self):
        self.store.settings["selected_topics"] = sorted(self.selected)
        self.store.settings["bag"] = []
        self.store.save_settings()
        self._draw_topics()

    def _mode_changed(self, value):
        self.store.settings["time_mode"] = "quick" if value.startswith("Quick") else "random"
        self.store.save_settings()

    def start(self):
        topics = sorted(self.selected)
        q = picker.next_question(self.store, topics)
        if q is None:
            self.app.toast("No questions for these topics. Add some in the Library.")
            return
        minutes = picker.random_minutes(q, self.store.settings.get("time_mode", "random"))
        self.app.show("session", question=q, minutes=minutes)


# ===================================================================== SESSION
class SessionScreen(ctk.CTkFrame):
    def __init__(self, parent, app, question: Question, minutes: float):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.store = app.store
        self.q = question
        self.total = minutes * 60
        self.elapsed = 0.0
        self.state = "ready"        # ready, running, paused
        self._last_tick = None
        self._job = None
        self.recorder = audio.Recorder()
        self.rec_path = None
        self.columnconfigure(0, weight=1)

        # top bar -----------------------------------------------------------
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 10))
        top.columnconfigure(1, weight=1)
        w.button(top, "Home", self.go_home, kind="ghost", icon_name="chevron-left",
                 size="sm", width=90).grid(row=0, column=0, sticky="w")
        tags = ctk.CTkFrame(top, fg_color="transparent")
        tags.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(tags, text=f"  {question.topic}", image=t.icon(t.topic_icon(question.topic),
                     16, t.TEAL), compound="left", font=t.font(13, "bold"),
                     text_color=t.TEAL).pack(side="left", padx=6)
        w.tag(tags, question.difficulty.capitalize(), "muted").pack(side="left", padx=4)

        # question card ------------------------------------------------------
        qcard = w.card(self)
        qcard.grid(row=1, column=0, sticky="ew", padx=8)
        qcard.columnconfigure(0, weight=1)
        qlabel = w.label(qcard, question.question, 24, "bold", wraplength=760)
        qlabel.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 12))
        w.wrap_on_resize(qlabel, margin=60)

        hint_row = ctk.CTkFrame(qcard, fg_color="transparent")
        hint_row.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 18))
        hint_row.columnconfigure(1, weight=1)
        self.hint_btn = w.button(hint_row, "Show key phrases", self.toggle_hint, kind="ghost",
                                 icon_name="lightbulb", size="sm")
        self.hint_btn.grid(row=0, column=0, sticky="w")
        self.hint_flow = w.FlowFrame(hint_row)
        self.hint_visible = False
        if not question.key_phrases:
            self.hint_btn.configure(state="disabled", text="No key phrases for this question")

        # timer ----------------------------------------------------------------
        mid = w.card(self)
        mid.grid(row=2, column=0, sticky="ew", padx=8, pady=(14, 0))
        mid.columnconfigure(0, weight=1)
        self.ring = w.TimerRing(mid, size=250)
        self.ring.grid(row=0, column=0, pady=(20, 4))
        self.status = w.label(mid, "Take a moment to think, then press Start speaking.", 14,
                              color=t.MUTED, anchor="center", justify="center")
        self.status.grid(row=1, column=0, pady=(0, 6))
        self.meter = ctk.CTkProgressBar(mid, width=240, height=8, progress_color=t.TEAL,
                                        fg_color=t.NEUTRAL_BTN)
        self.meter.set(0)
        self.meter.grid(row=2, column=0, pady=(0, 8))
        self.meter.grid_remove()

        self.controls = ctk.CTkFrame(mid, fg_color="transparent")
        self.controls.grid(row=3, column=0, pady=(6, 22))
        self._draw_ready_controls()
        self._update_ring()

        self.app.bind_key("<space>", self._space)

    # --------------------------------------------------------------- controls
    def _clear_controls(self):
        for child in self.controls.winfo_children():
            child.destroy()

    def _draw_ready_controls(self):
        self._clear_controls()
        w.button(self.controls, "  Start speaking", self.begin, icon_name="mic",
                 size="lg", width=280).pack(side="left", padx=6)
        w.button(self.controls, "New question", self.new_question, kind="neutral",
                 icon_name="shuffle", height=64, width=170).pack(side="left", padx=6)

    def _draw_running_controls(self):
        self._clear_controls()
        paused = self.state == "paused"
        w.button(self.controls, "Resume" if paused else "Pause", self.toggle_pause,
                 kind="neutral", icon_name="play" if paused else "pause",
                 height=56, width=150).pack(side="left", padx=6)
        w.button(self.controls, "Finish", self.finish, kind="teal", icon_name="check",
                 height=56, width=170).pack(side="left", padx=6)

    def toggle_hint(self):
        self.hint_visible = not self.hint_visible
        if self.hint_visible:
            self.hint_flow.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            self.hint_flow.clear()
            for phrase in self.q.key_phrases:
                self.hint_flow.add(w.tag(self.hint_flow, phrase, "teal"))
            self.hint_btn.configure(text="Hide key phrases")
        else:
            self.hint_flow.grid_forget()
            self.hint_btn.configure(text="Show key phrases")

    # ------------------------------------------------------------------ timer
    def _update_ring(self):
        remaining = max(0.0, self.total - self.elapsed)
        planned = w.fmt_duration(self.total)
        small = {"ready": f"of {planned}", "running": "remaining",
                 "paused": "paused"}[self.state]
        color = t.TEAL if self.state == "ready" else t.ACCENT
        self.ring.set(remaining / self.total if self.total else 0, w.fmt_seconds(remaining),
                      small, color)

    def begin(self):
        self.state = "running"
        self._last_tick = time.monotonic()
        if self.store.settings.get("record_audio", True):
            if self.recorder.start():
                self.meter.grid()
                self.status.configure(text="Recording. Speak until the ring is empty.")
            else:
                self.status.configure(text=f"Timer running without recording. {self.recorder.error}")
        else:
            self.status.configure(text="Timer running. Recording is off in Settings.")
        self._draw_running_controls()
        self._tick()

    def _tick(self):
        now = time.monotonic()
        if self.state == "running":
            self.elapsed += now - self._last_tick
        self._last_tick = now
        self._update_ring()
        if self.recorder.active:
            self.meter.set(self.recorder.level)
        if self.elapsed >= self.total:
            if self.store.settings.get("beep", True):
                audio.beep(self)
            self.finish()
            return
        self._job = self.after(100, self._tick)

    def toggle_pause(self):
        self.state = "running" if self.state == "paused" else "paused"
        self.recorder.pause(self.state == "paused")
        self.status.configure(text="Paused." if self.state == "paused"
                              else "Recording. Speak until the ring is empty."
                              if self.recorder.active else "Timer running.")
        self._draw_running_controls()
        self._update_ring()

    def _space(self, _event=None):
        if self.state == "ready":
            self.begin()
        else:
            self.toggle_pause()

    def _stop_everything(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.app.unbind_key("<space>")

    def finish(self):
        self._stop_everything()
        path = None
        if self.recorder.active:
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            path = self.recorder.stop(paths.recordings_dir() / f"{stamp}_{self.q.id}.wav")
        self.app.show("review", question=self.q, planned=self.total,
                      spoken=min(self.elapsed, self.total), recording=path)

    def new_question(self):
        self._stop_everything()
        topics = self.store.settings.get("selected_topics", [])
        q = picker.next_question(self.store, topics, exclude=self.q.id) or self.q
        minutes = picker.random_minutes(q, self.store.settings.get("time_mode", "random"))
        self.app.show("session", question=q, minutes=minutes)

    def go_home(self):
        self._stop_everything()
        if self.recorder.active:
            self.recorder.stop(None)
        self.app.show("home")

    def destroy(self):
        self._stop_everything()
        if self.recorder.active:
            self.recorder.stop(None)
        super().destroy()


# ====================================================================== REVIEW
class ReviewScreen(ctk.CTkScrollableFrame):
    def __init__(self, parent, app, question: Question, planned: float, spoken: float,
                 recording=None):
        super().__init__(parent, fg_color="transparent", scrollbar_button_color=t.BORDER,
                         scrollbar_button_hover_color=t.MUTED)
        self.app = app
        self.store = app.store
        self.q = question
        self.planned, self.spoken, self.recording = planned, spoken, recording
        self.rating = 0
        self.player = audio.Player()
        self.columnconfigure(0, weight=1)

        title = "Time is up. Nice work." if spoken >= planned - 0.5 else "Session finished."
        w.label(self, title, 28, "bold").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
        w.label(self, f"You spoke for {w.fmt_duration(spoken)} of {w.fmt_duration(planned)}.",
                15, color=t.MUTED).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 14))

        # question + recording ---------------------------------------------
        top = w.card(self)
        top.grid(row=2, column=0, sticky="ew", padx=8)
        top.columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=f"  {question.topic}", image=t.icon(t.topic_icon(question.topic),
                     16, t.TEAL), compound="left", font=t.font(13, "bold"),
                     text_color=t.TEAL).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 4))
        ql = w.label(top, question.question, 19, "bold", wraplength=760)
        ql.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 14))
        w.wrap_on_resize(ql, margin=60)

        rec = ctk.CTkFrame(top, fg_color=t.BG, corner_radius=12)
        rec.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 20))
        rec.columnconfigure(1, weight=1)
        if recording:
            self.play_btn = w.button(rec, "Play my answer", self.toggle_play, kind="teal",
                                     icon_name="play", width=170)
            self.play_btn.grid(row=0, column=0, padx=12, pady=12)
            w.label(rec, f"Recording, {w.fmt_duration(audio.duration_seconds(recording))}",
                    13, color=t.MUTED).grid(row=0, column=1, sticky="w")
            w.icon_button(rec, "folder-open", lambda: app.open_path(paths.recordings_dir()),
                          "Open recordings folder", t.MUTED).grid(row=0, column=2, padx=8)
        else:
            w.label(rec, "No recording for this session.", 13, color=t.MUTED).grid(
                row=0, column=0, padx=16, pady=14, sticky="w")

        # reference -----------------------------------------------------------
        ref = w.card(self)
        ref.grid(row=3, column=0, sticky="ew", padx=8, pady=(14, 0))
        ref.columnconfigure(0, weight=1)
        w.label(ref, "Reference answer", 16, "bold").grid(row=0, column=0, sticky="w",
                                                          padx=22, pady=(18, 8))
        lines = max(5, min(14, len(question.reference_answer) // 85 + 2))
        w.readonly_text(ref, question.reference_answer, height=lines * 22).grid(
            row=1, column=0, sticky="ew", padx=22)
        if question.key_phrases:
            w.label(ref, "Phrases to try next time", 13, "bold", color=t.MUTED).grid(
                row=2, column=0, sticky="w", padx=22, pady=(14, 6))
            flow = w.FlowFrame(ref)
            flow.grid(row=3, column=0, sticky="ew", padx=22)
            for phrase in question.key_phrases:
                flow.add(w.tag(flow, phrase, "teal"))
        ctk.CTkLabel(ref, text="", height=6).grid(row=4, column=0)

        # rating -----------------------------------------------------------------
        rate = w.card(self)
        rate.grid(row=4, column=0, sticky="ew", padx=8, pady=(14, 0))
        rate.columnconfigure(0, weight=1)
        w.label(rate, "How did it go?", 16, "bold").grid(row=0, column=0, sticky="w",
                                                         padx=22, pady=(18, 8))
        self.rate_row = ctk.CTkFrame(rate, fg_color="transparent")
        self.rate_row.grid(row=1, column=0, sticky="w", padx=18)
        self._draw_rating()
        self.note = ctk.CTkEntry(rate, placeholder_text="Note for next time (optional)",
                                 height=40, font=t.font(14), fg_color=t.BG,
                                 border_color=t.BORDER, text_color=t.INK, corner_radius=10)
        self.note.grid(row=2, column=0, sticky="ew", padx=22, pady=(12, 20))

        # actions ----------------------------------------------------------------
        act = ctk.CTkFrame(self, fg_color="transparent")
        act.grid(row=5, column=0, sticky="ew", padx=8, pady=(18, 12))
        w.button(act, "Save and next question", lambda: self.save(next_q=True),
                 icon_name="skip-forward", width=240, height=50).pack(side="left")
        w.button(act, "Save and go home", lambda: self.save(next_q=False), kind="neutral",
                 icon_name="house", width=190, height=50).pack(side="left", padx=10)
        if question.source != "drive":
            w.button(act, "Edit question", self.edit, kind="ghost", icon_name="pencil",
                     height=50).pack(side="left")
        else:
            w.button(act, "Edit in Google Sheet", app.open_sheet, kind="ghost",
                     icon_name="external-link", height=50).pack(side="left")

    def _draw_rating(self):
        for child in self.rate_row.winfo_children():
            child.destroy()
        for value, text in RATINGS:
            chosen = value == self.rating
            ctk.CTkButton(
                self.rate_row, text=f"{value}  {text}", width=112, height=40, corner_radius=10,
                font=t.font(13, "bold" if chosen else "normal"),
                fg_color=t.ACCENT if chosen else t.NEUTRAL_BTN,
                hover_color=t.ACCENT_HOVER if chosen else t.NEUTRAL_HOVER,
                text_color=t.WHITE if chosen else t.INK,
                command=lambda v=value: self._rate(v)).pack(side="left", padx=4)

    def _rate(self, value):
        self.rating = value
        self._draw_rating()

    def toggle_play(self):
        if self.player.playing:
            self.player.stop()
            self._play_state(False)
        elif self.player.play(self.recording, on_done=lambda: self.app.call_soon(
                lambda: self._play_state(False))):
            self._play_state(True)
        else:
            self.app.toast(self.player.error)

    def _play_state(self, playing):
        if self.winfo_exists():
            self.play_btn.configure(text="Stop" if playing else "Play my answer",
                                    image=t.icon("square" if playing else "play", 18, t.WHITE))

    def save(self, next_q: bool):
        self.player.stop()
        self.store.add_session({
            "question_id": self.q.id,
            "topic": self.q.topic,
            "question": self.q.question,
            "planned_seconds": round(self.planned),
            "spoken_seconds": round(self.spoken),
            "rating": self.rating or None,
            "note": self.note.get().strip(),
            "recording": self.recording.name if self.recording else "",
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        })
        if next_q:
            topics = self.store.settings.get("selected_topics", [])
            q = picker.next_question(self.store, topics, exclude=self.q.id) or self.q
            minutes = picker.random_minutes(q, self.store.settings.get("time_mode", "random"))
            self.app.show("session", question=q, minutes=minutes)
        else:
            self.app.show("home")

    def edit(self):
        from .library import QuestionEditor
        QuestionEditor(self.app, self.q, on_saved=lambda q: self.app.toast("Question saved."))

    def destroy(self):
        self.player.stop()
        super().destroy()

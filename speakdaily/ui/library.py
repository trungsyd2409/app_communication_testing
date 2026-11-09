"""Question library: search, filter, add, edit, delete, import and export."""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import picker
from .. import theme as t
from ..storage import Question
from . import widgets as w

SOURCE_LABEL = {"drive": ("Sheet", "teal"), "local": ("Mine", "accent"),
                "starter": ("Built-in", "muted")}
PAGE = 25
MINUTE_CHOICES = [f"{m / 2:g}" for m in range(2, 21)]   # 1 .. 10 in half minutes


class LibraryScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.store = app.store
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 12))
        head.columnconfigure(0, weight=1)
        w.label(head, "Library", 28, "bold").grid(row=0, column=0, sticky="w")
        btns = ctk.CTkFrame(head, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")
        w.button(btns, "Add question", self.add, icon_name="plus").pack(side="left", padx=4)
        w.button(btns, "Import CSV", self.import_csv, kind="neutral",
                 icon_name="upload").pack(side="left", padx=4)
        w.button(btns, "Export CSV", self.export_csv, kind="neutral",
                 icon_name="download").pack(side="left", padx=4)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 10))
        bar.columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(bar, height=40, font=t.font(14),
                             placeholder_text="Search questions and answers",
                             fg_color=t.SURFACE, border_color=t.BORDER, text_color=t.INK,
                             corner_radius=10)
        entry.grid(row=0, column=0, sticky="ew")
        entry.bind("<KeyRelease>", lambda _: self._schedule_refresh())
        self.search = entry
        self.topic = ctk.StringVar(value="All topics")
        self.topic_menu = ctk.CTkOptionMenu(
            bar, variable=self.topic, values=["All topics"] + self.store.topics(),
            command=lambda _: self.refresh(), height=40, width=190, font=t.font(13),
            fg_color=t.NEUTRAL_BTN, button_color=t.NEUTRAL_HOVER,
            button_hover_color=t.BORDER, text_color=t.INK, corner_radius=10,
            dropdown_font=t.font(13))
        self.topic_menu.grid(row=0, column=1, padx=(10, 0))

        self.list = w.scroll_frame(self)
        self.list.grid(row=2, column=0, sticky="nsew", padx=0)
        self.list.columnconfigure(0, weight=1)
        self.count = w.label(self, "", 12, color=t.MUTED)
        self.count.grid(row=3, column=0, sticky="w", padx=10, pady=(6, 0))
        self._job = None
        self.refresh()

    def _schedule_refresh(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self.refresh)

    def _matches(self) -> list[Question]:
        text = self.search.get().strip().lower()
        topic = self.topic.get()
        items = []
        for q in self.store.questions:
            if topic != "All topics" and q.topic != topic:
                continue
            if text and text not in (q.question + " " + q.reference_answer + " " +
                                     q.topic + " " + " ".join(q.key_phrases)).lower():
                continue
            items.append(q)
        return sorted(items, key=lambda q: (q.topic.lower(), q.question.lower()))

    def refresh(self):
        self._job = None
        for child in self.list.winfo_children():
            child.destroy()
        self.topic_menu.configure(values=["All topics"] + self.store.topics())
        self.items = self._matches()
        self.shown = 0
        self.more_btn = None
        if not self.items:
            w.label(self.list, "No questions match. Try another search or add a question.",
                    14, color=t.MUTED).grid(row=0, column=0, padx=10, pady=30)
        self.show_more()
        self.count.configure(text=f"{len(self.items)} of {len(self.store.questions)} questions")
        self.list._parent_canvas.yview_moveto(0)

    def show_more(self):
        if self.more_btn is not None:
            self.more_btn.destroy()
            self.more_btn = None
        end = min(len(self.items), self.shown + PAGE)
        for i in range(self.shown, end):
            self._row(i, self.items[i])
        self.shown = end
        if self.shown < len(self.items):
            self.more_btn = w.button(self.list, f"Show more ({len(self.items) - self.shown} left)",
                                     self.show_more, kind="neutral")
            self.more_btn.grid(row=self.shown, column=0, pady=10)

    def _row(self, i, q: Question):
        row = w.card(self.list)
        row.grid(row=i, column=0, sticky="ew", padx=8, pady=4)
        row.columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text="", image=t.icon(t.topic_icon(q.topic), 20, t.TEAL)).grid(
            row=0, column=0, rowspan=2, padx=(16, 10), pady=12)
        text = q.question if len(q.question) < 120 else q.question[:117] + "..."
        w.label(row, text, 14, "bold").grid(row=0, column=1, sticky="w", pady=(12, 0))
        src_text, _ = SOURCE_LABEL.get(q.source, ("Mine", "accent"))
        meta = (f"{q.topic}   ·   {picker.format_minutes(q.min_minutes)} to "
                f"{picker.format_minutes(q.max_minutes)}   ·   {src_text}"
                + ("" if q.reference_answer else "   ·   no answer yet"))
        w.label(row, meta, 12, color=t.MUTED).grid(row=1, column=1, sticky="w", pady=(2, 12))

        acts = ctk.CTkFrame(row, fg_color="transparent")
        acts.grid(row=0, column=2, rowspan=2, padx=10)
        w.icon_button(acts, "play", lambda: self.practise(q), "Practise this question",
                      t.ACCENT).pack(side="left")
        w.icon_button(acts, "pencil", lambda: self.edit(q),
                      "View" if q.source == "drive" else "Edit").pack(side="left")
        if q.source != "drive":
            w.icon_button(acts, "trash-2", lambda: self.delete(q), "Delete",
                          t.MUTED).pack(side="left")

    # ---------------------------------------------------------------- actions
    def practise(self, q):
        minutes = picker.random_minutes(q, self.store.settings.get("time_mode", "random"))
        self.app.show("session", question=q, minutes=minutes)

    def add(self):
        QuestionEditor(self.app, None, on_saved=lambda _: self.refresh())

    def edit(self, q):
        QuestionEditor(self.app, q, on_saved=lambda _: self.refresh())

    def delete(self, q):
        if messagebox.askyesno("Delete question", f"Delete this question?\n\n{q.question}",
                               parent=self.app):
            self.store.delete(q.id)
            self.refresh()

    def import_csv(self):
        name = filedialog.askopenfilename(parent=self.app, title="Import questions",
                                          filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not name:
            return
        try:
            count = self.store.import_csv(Path(name))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            messagebox.showerror("Import failed", str(exc), parent=self.app)
            return
        self.app.toast(f"Imported {count} questions.")
        self.refresh()

    def export_csv(self):
        name = filedialog.asksaveasfilename(parent=self.app, title="Export questions",
                                            defaultextension=".csv",
                                            initialfile="speakdaily_questions.csv",
                                            filetypes=[("CSV files", "*.csv")])
        if not name:
            return
        count = self.store.export_csv(Path(name), self._matches())
        self.app.toast(f"Exported {count} questions. You can paste them into your Google Sheet.")


class QuestionEditor(ctk.CTkToplevel):
    """Add or edit one question. Sheet questions are read-only here."""

    def __init__(self, app, q: Question | None, on_saved=None):
        super().__init__(app)
        self.app = app
        self.store = app.store
        self.q = q
        self.on_saved = on_saved
        self.readonly = bool(q and q.source == "drive")
        self.title("Edit question" if q else "New question")
        self.geometry("720x720")
        self.minsize(560, 560)
        self.configure(fg_color=t.BG)
        self.transient(app)
        self.after(150, self._grab)

        body = w.scroll_frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=(16, 0))
        body.columnconfigure(0, weight=1)

        r = 0
        if self.readonly:
            note = ctk.CTkFrame(body, fg_color=t.TEAL_SOFT, corner_radius=12)
            note.grid(row=r, column=0, sticky="ew", pady=(0, 12))
            note.columnconfigure(0, weight=1)
            w.label(note, "This question comes from your Google Sheet. Edit it in the sheet, "
                          "then press Sync, so your change is not lost at the next sync.",
                    13, color=t.TEAL, wraplength=520).grid(row=0, column=0, padx=14, pady=12,
                                                           sticky="w")
            w.button(note, "Open sheet", app.open_sheet, kind="teal", icon_name="external-link",
                     size="sm").grid(row=0, column=1, padx=12)
            r += 1

        def field_label(text):
            nonlocal r
            w.label(body, text, 13, "bold", color=t.MUTED).grid(row=r, column=0, sticky="w",
                                                                pady=(10, 4))
            r += 1

        field_label("Topic")
        self.topic = ctk.CTkComboBox(body, values=self.store.topics() or ["General"], height=40,
                                     font=t.font(14), dropdown_font=t.font(13),
                                     fg_color=t.SURFACE, border_color=t.BORDER,
                                     button_color=t.NEUTRAL_BTN, text_color=t.INK,
                                     corner_radius=10)
        self.topic.set(q.topic if q else (self.store.topics() or ["General"])[0])
        self.topic.grid(row=r, column=0, sticky="ew")
        r += 1

        field_label("Question")
        self.question = self._textbox(body, q.question if q else "", 80)
        self.question.grid(row=r, column=0, sticky="ew")
        r += 1

        field_label("Reference answer")
        self.answer = self._textbox(body, q.reference_answer if q else "", 200)
        self.answer.grid(row=r, column=0, sticky="ew")
        r += 1

        field_label("Key phrases (separate with ;)")
        self.phrases = ctk.CTkEntry(body, height=40, font=t.font(14), fg_color=t.SURFACE,
                                    border_color=t.BORDER, text_color=t.INK, corner_radius=10)
        self.phrases.insert(0, "; ".join(q.key_phrases) if q else "")
        self.phrases.grid(row=r, column=0, sticky="ew")
        r += 1

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.grid(row=r, column=0, sticky="ew", pady=(12, 0))
        r += 1
        w.label(grid, "Difficulty", 13, "bold", color=t.MUTED).grid(row=0, column=0, sticky="w")
        w.label(grid, "Min minutes", 13, "bold", color=t.MUTED).grid(row=0, column=1, sticky="w",
                                                                     padx=(18, 0))
        w.label(grid, "Max minutes", 13, "bold", color=t.MUTED).grid(row=0, column=2, sticky="w",
                                                                     padx=(18, 0))
        self.difficulty = w.segmented(grid, ["easy", "medium", "hard"])
        self.difficulty.set(q.difficulty if q else "medium")
        self.difficulty.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.min_m = self._minutes(grid, q.min_minutes if q else 1)
        self.min_m.grid(row=1, column=1, padx=(18, 0), pady=(4, 0))
        self.max_m = self._minutes(grid, q.max_minutes if q else 10)
        self.max_m.grid(row=1, column=2, padx=(18, 0), pady=(4, 0))

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=16, pady=16)
        w.button(foot, "Cancel", self.destroy, kind="neutral").pack(side="right", padx=(8, 0))
        if not self.readonly:
            w.button(foot, "Save question", self.save, icon_name="check").pack(side="right")

        if self.readonly:
            for widget in (self.topic, self.phrases, self.difficulty, self.min_m, self.max_m):
                widget.configure(state="disabled")
            for box in (self.question, self.answer):
                box.configure(state="disabled")

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _textbox(self, parent, text, height):
        box = ctk.CTkTextbox(parent, height=height, wrap="word", font=t.font(14),
                             fg_color=t.SURFACE, border_color=t.BORDER, border_width=1,
                             text_color=t.INK, corner_radius=10)
        box.insert("1.0", text)
        return box

    def _minutes(self, parent, value):
        menu = ctk.CTkOptionMenu(parent, values=MINUTE_CHOICES, width=100, height=36,
                                 font=t.font(13), fg_color=t.NEUTRAL_BTN,
                                 button_color=t.NEUTRAL_HOVER, button_hover_color=t.BORDER,
                                 text_color=t.INK, dropdown_font=t.font(13))
        menu.set(f"{value:g}")
        return menu

    def save(self):
        question = self.question.get("1.0", "end").strip()
        if not question:
            messagebox.showwarning("Missing question", "Please write the question.", parent=self)
            return
        lo, hi = float(self.min_m.get()), float(self.max_m.get())
        if lo > hi:
            lo, hi = hi, lo
        q = Question(
            id=self.q.id if self.q else self.store.new_id(),
            topic=self.topic.get().strip() or "General",
            question=question,
            reference_answer=self.answer.get("1.0", "end").strip(),
            key_phrases=[p.strip() for p in self.phrases.get().split(";") if p.strip()],
            difficulty=self.difficulty.get() or "medium",
            min_minutes=lo, max_minutes=hi,
            tags=list(self.q.tags) if self.q else [],
            source=self.q.source if self.q else "local",
        )
        self.store.upsert(q)
        if self.on_saved:
            self.on_saved(q)
        self.destroy()

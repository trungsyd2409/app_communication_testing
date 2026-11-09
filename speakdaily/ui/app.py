"""Main window: sidebar navigation, screen switching, background sync, toasts."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from .. import drive_sync, paths
from .. import theme as t
from ..storage import Store
from . import widgets as w
from .history import HistoryScreen
from .library import LibraryScreen
from .practice import HomeScreen, ReviewScreen, SessionScreen
from .settings import SettingsScreen

SCREENS = {
    "home": HomeScreen,
    "session": SessionScreen,
    "review": ReviewScreen,
    "library": LibraryScreen,
    "history": HistoryScreen,
    "settings": SettingsScreen,
}
NAV = [("home", "Practice", "mic"), ("library", "Library", "library"),
       ("history", "History", "chart-column"), ("settings", "Settings", "settings")]
NAV_OF = {"session": "home", "review": "home"}


class App(ctk.CTk):
    def __init__(self, store: Store | None = None):
        super().__init__()
        self.store = store or Store()
        self._queue: queue.Queue = queue.Queue()
        self._syncing = False
        self._toast = None
        self._keys: dict[str, str] = {}
        self.current = None
        self.current_name = ""

        self.apply_appearance(redraw=False)
        self.title("SpeakDaily")
        self.geometry("1120x760")
        self.minsize(920, 640)
        self.configure(fg_color=t.BG)
        ico = paths.asset("app.ico")
        if sys.platform == "win32" and ico.exists():
            try:
                self.iconbitmap(str(ico))
            except Exception:
                pass

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.show("home")
        self.after(100, self._poll)
        if self.store.settings.get("auto_sync") and self.store.settings.get("sheet_url"):
            self.after(600, self.sync_now)

    # ---------------------------------------------------------------- layout
    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, fg_color=t.SIDEBAR, corner_radius=0, width=210)
        bar.grid(row=0, column=0, sticky="ns")
        bar.grid_propagate(False)
        bar.columnconfigure(0, weight=1)
        logo = ctk.CTkFrame(bar, fg_color="transparent")
        logo.grid(row=0, column=0, sticky="w", padx=18, pady=(22, 26))
        ctk.CTkLabel(logo, text="", image=t.icon("message-circle", 28, t.ACCENT)).pack(side="left")
        w.label(logo, " SpeakDaily", 19, "bold").pack(side="left")
        self.nav_buttons = {}
        for i, (name, text, icon_name) in enumerate(NAV, start=1):
            btn = ctk.CTkButton(bar, text=f"  {text}", anchor="w", height=44, corner_radius=12,
                                font=t.font(14, "bold"), image=t.icon(icon_name, 20, t.INK),
                                fg_color="transparent", hover_color=t.NEUTRAL_HOVER,
                                text_color=t.INK, command=lambda n=name: self.show(n))
            btn.grid(row=i, column=0, sticky="ew", padx=12, pady=3)
            self.nav_buttons[name] = (btn, icon_name)
        bar.rowconfigure(10, weight=1)
        w.label(bar, "Space: start / pause", 11, color=t.MUTED).grid(row=11, column=0, sticky="w",
                                                                     padx=22, pady=(0, 18))

    def _highlight(self, name):
        active = NAV_OF.get(name, name)
        for key, (btn, icon_name) in self.nav_buttons.items():
            on = key == active
            btn.configure(fg_color=t.SURFACE if on else "transparent",
                          text_color=t.ACCENT if on else t.INK,
                          image=t.icon(icon_name, 20, t.ACCENT if on else t.INK))

    def show(self, name: str, **kwargs):
        if self.current is not None:
            self.current.destroy()
        self.current = SCREENS[name](self.content, self, **kwargs)
        self.current.grid(row=0, column=0, sticky="nsew")
        self.current_name = name
        self._highlight(name)

    def apply_appearance(self, redraw=True):
        look = self.store.settings.get("appearance", "light")
        ctk.set_appearance_mode({"dark": "dark", "system": "system"}.get(look, "light"))
        if redraw and self.current_name:
            self.show(self.current_name if self.current_name not in ("session", "review")
                      else "home")

    # ------------------------------------------------------------- utilities
    def bind_key(self, sequence, func):
        self._keys[sequence] = self.bind(sequence, func)

    def unbind_key(self, sequence):
        if sequence in self._keys:
            self.unbind(sequence, self._keys.pop(sequence))

    def call_soon(self, func):
        """Run func on the Tk thread (safe to call from worker threads)."""
        self._queue.put(func)

    def _poll(self):
        try:
            while True:
                self._queue.get_nowait()()
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def toast(self, text: str, seconds: float = 4):
        if self._toast is not None:
            self._toast.destroy()
        self._toast = ctk.CTkLabel(self, text=f"   {text}   ", fg_color=t.INK, text_color=t.BG,
                                   corner_radius=12, font=t.font(13), height=40)
        self._toast.place(relx=0.5, rely=0.96, anchor="s")
        toast = self._toast
        self.after(int(seconds * 1000), lambda: toast.winfo_exists() and toast.destroy())

    def open_path(self, path: Path):
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            self.toast(f"Cannot open folder: {exc}")

    def open_sheet(self):
        link = self.store.settings.get("sheet_url", "")
        try:
            webbrowser.open(drive_sync.sheet_url(drive_sync.parse_link(link)))
        except drive_sync.SyncError as exc:
            self.toast(str(exc))

    # ------------------------------------------------------------------ sync
    def sync_status_text(self) -> str:
        s = self.store.settings
        n = len(self.store.questions)
        if self._syncing:
            return "Syncing with Google Drive..."
        if not s.get("sheet_url"):
            return f"{n} built-in and local questions. Connect a Google Sheet to edit them anywhere."
        if s.get("last_sync"):
            try:
                when = datetime.fromisoformat(s["last_sync"]).strftime("%d %b %H:%M")
            except ValueError:
                when = s["last_sync"]
            return f"{n} questions. Last sync from Google Sheet: {when}."
        return f"{n} questions. Not synced yet."

    def sync_now(self, on_done=None):
        if self._syncing:
            return
        link = self.store.settings.get("sheet_url", "")
        mode = self.store.settings.get("sync_mode", "link")
        self._syncing = True
        self._refresh_sync_label()

        def work():
            try:
                questions = drive_sync.fetch_questions(link, mode)
                self.call_soon(lambda: self._sync_ok(questions, on_done))
            except drive_sync.SyncError as exc:
                msg = str(exc)
                self.call_soon(lambda: self._sync_failed(msg, on_done))
            except Exception as exc:     # never crash the UI because of sync
                msg = f"Sync failed: {exc}"
                self.call_soon(lambda: self._sync_failed(msg, on_done))

        threading.Thread(target=work, daemon=True).start()

    def _sync_ok(self, questions, on_done):
        self._syncing = False
        count = self.store.replace_drive_questions(questions)
        self.store.settings["last_sync"] = datetime.now().isoformat(timespec="seconds")
        self.store.settings["last_sync_count"] = count
        self.store.settings["bag"] = []
        self.store.save_settings()
        self.toast(f"Synced {count} questions from Google Drive.")
        if self.current_name in ("home", "library"):
            self.show(self.current_name)
        if on_done:
            on_done()

    def _sync_failed(self, message, on_done):
        self._syncing = False
        self.toast(message, seconds=8)
        self._refresh_sync_label()
        if on_done:
            on_done()

    def _refresh_sync_label(self):
        label = getattr(self.current, "sync_label", None)
        if label is not None and label.winfo_exists():
            label.configure(text=self.sync_status_text())

"""Settings: Google Sheet connection, practice options, appearance, data folder."""
from __future__ import annotations

import customtkinter as ctk

from .. import __version__, audio, drive_sync, paths
from .. import theme as t
from . import widgets as w

MODES = {"Shared link (no login)": "link", "Google sign-in": "google"}


class SettingsScreen(ctk.CTkScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent", scrollbar_button_color=t.BORDER,
                         scrollbar_button_hover_color=t.MUTED)
        self.app = app
        self.store = app.store
        s = self.store.settings
        self.columnconfigure(0, weight=1)

        w.label(self, "Settings", 28, "bold").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 14))

        # Google Drive --------------------------------------------------------
        g = self._section(1, "cloud", "Google Drive question sheet",
                          "Keep your questions in a Google Sheet. Edit them there on any "
                          "device, then press Sync.")
        self.url = ctk.CTkEntry(g, height=40, font=t.font(13), fg_color=t.BG,
                                border_color=t.BORDER, text_color=t.INK, corner_radius=10,
                                placeholder_text="https://docs.google.com/spreadsheets/d/...")
        if s.get("sheet_url"):
            self.url.insert(0, s["sheet_url"])
        self.url.grid(row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=(4, 10))

        w.label(g, "Connect with", 13, "bold", color=t.MUTED).grid(row=3, column=0, sticky="w",
                                                                   padx=20)
        current = next((k for k, v in MODES.items() if v == s.get("sync_mode")),
                       "Shared link (no login)")
        self.mode = w.segmented(g, list(MODES), command=lambda _: self._mode_help())
        self.mode.set(current)
        self.mode.grid(row=4, column=0, columnspan=3, sticky="w", padx=20, pady=(4, 6))
        self.mode_help = w.label(g, "", 12, color=t.MUTED, wraplength=640)
        self.mode_help.grid(row=5, column=0, columnspan=3, sticky="w", padx=20)
        self._mode_help()

        self.auto = ctk.BooleanVar(value=s.get("auto_sync", True))
        self._switch(g, 6, "Sync when the app starts", self.auto)

        btns = ctk.CTkFrame(g, fg_color="transparent")
        btns.grid(row=7, column=0, columnspan=3, sticky="w", padx=16, pady=(8, 6))
        w.button(btns, "Save and sync", self.save_and_sync, icon_name="refresh-cw").pack(
            side="left", padx=4)
        w.button(btns, "Open sheet", app.open_sheet, kind="neutral",
                 icon_name="external-link").pack(side="left", padx=4)
        w.button(btns, "Open data folder", lambda: app.open_path(paths.data_dir()),
                 kind="ghost", icon_name="folder-open").pack(side="left", padx=4)
        if drive_sync.token_path().exists():
            w.button(btns, "Sign out of Google", self.sign_out, kind="ghost",
                     icon_name="x").pack(side="left", padx=4)
        self.sync_info = w.label(g, app.sync_status_text(), 12, color=t.MUTED)
        self.sync_info.grid(row=8, column=0, columnspan=3, sticky="w", padx=20, pady=(4, 18))

        # practice ------------------------------------------------------------
        p = self._section(2, "timer", "Practice")
        self.record = ctk.BooleanVar(value=s.get("record_audio", True))
        self._switch(p, 2, "Record my voice during a session", self.record)
        self.beep = ctk.BooleanVar(value=s.get("beep", True))
        self._switch(p, 3, "Play a sound when time is up", self.beep)
        w.label(p, "Keep the newest recordings", 13).grid(row=4, column=0, sticky="w", padx=20,
                                                          pady=(10, 18))
        self.keep = ctk.CTkOptionMenu(p, values=["20", "60", "150", "500"], width=90,
                                      font=t.font(13), fg_color=t.NEUTRAL_BTN,
                                      button_color=t.NEUTRAL_HOVER, text_color=t.INK,
                                      command=lambda _: self.save())
        self.keep.set(str(s.get("keep_recordings", 60)))
        self.keep.grid(row=4, column=1, sticky="w", pady=(10, 18))
        if not audio.AUDIO_OK:
            w.label(p, f"Audio is not available: {audio.AUDIO_ERROR}", 12, color=t.ACCENT).grid(
                row=5, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 14))

        # appearance ------------------------------------------------------------
        a = self._section(3, "sun", "Appearance")
        self.look = w.segmented(a, ["Light", "Dark", "System"], command=self.set_look)
        self.look.set(s.get("appearance", "light").capitalize())
        self.look.grid(row=2, column=0, sticky="w", padx=20, pady=(4, 18))

        w.label(self, f"SpeakDaily {__version__}   ·   Data folder: {paths.data_dir()}", 12,
                color=t.MUTED).grid(row=4, column=0, sticky="w", padx=10, pady=(16, 10))

    # ----------------------------------------------------------------- helpers
    def _section(self, row, icon_name, title, subtitle=""):
        box = w.card(self)
        box.grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 14))
        box.columnconfigure(2, weight=1)
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(head, text="", image=t.icon(icon_name, 20, t.ACCENT)).pack(side="left")
        w.label(head, f"  {title}", 16, "bold").pack(side="left")
        if subtitle:
            w.label(box, subtitle, 13, color=t.MUTED, wraplength=640).grid(
                row=1, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 6))
        return box

    def _switch(self, parent, row, text, var):
        w.checkbox(parent, text, var, command=self.save).grid(row=row, column=0, columnspan=3, sticky="w",
                                              padx=20, pady=(10, 0))

    def _mode_help(self):
        if MODES[self.mode.get()] == "link":
            text = ("In Google Sheets press Share, set General access to 'Anyone with the "
                    "link' and role 'Viewer', then copy the link here. No login needed.")
        else:
            text = ("For private sheets. Put your OAuth 'credentials.json' in the data folder "
                    "(see README). The first sync opens your browser to sign in. Read-only access.")
        self.mode_help.configure(text=text)

    def save(self):
        s = self.store.settings
        s["sheet_url"] = self.url.get().strip()
        s["sync_mode"] = MODES[self.mode.get()]
        s["auto_sync"] = bool(self.auto.get())
        s["record_audio"] = bool(self.record.get())
        s["beep"] = bool(self.beep.get())
        s["keep_recordings"] = int(self.keep.get())
        self.store.save_settings()

    def save_and_sync(self):
        self.save()
        self.sync_info.configure(text="Syncing...")
        self.app.sync_now(on_done=lambda: self.winfo_exists() and self.sync_info.configure(
            text=self.app.sync_status_text()))

    def sign_out(self):
        drive_sync.sign_out()
        self.app.toast("Signed out of Google.")
        self.app.show("settings")

    def set_look(self, value):
        self.store.settings["appearance"] = value.lower()
        self.store.save_settings()
        self.app.apply_appearance()

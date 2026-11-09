"""Colours, fonts and icons. Warm paper background with one terracotta accent."""
from __future__ import annotations

import re
import sys
from functools import lru_cache

import customtkinter as ctk
from PIL import Image

from . import paths

# (light, dark) pairs, the format customtkinter expects.
BG = ("#F6F1E7", "#1F1D1A")
SURFACE = ("#FFFDF8", "#2A2724")
SIDEBAR = ("#ECE4D5", "#171513")
BORDER = ("#E2D8C6", "#3A3631")
INK = ("#2B2A28", "#F1ECE2")
MUTED = ("#7A7368", "#A89F92")
ACCENT = ("#C8553D", "#D9694F")
ACCENT_HOVER = ("#A9442F", "#C25A42")
ACCENT_SOFT = ("#F5DED5", "#4A2C24")
TEAL = ("#2F6F6A", "#5BA39C")
TEAL_HOVER = ("#245752", "#4A8C86")
TEAL_SOFT = ("#DCEBE8", "#22403D")
NEUTRAL_BTN = ("#E9E1D2", "#35312C")
NEUTRAL_HOVER = ("#DDD3C1", "#423D37")

FONT = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def font(size: int = 14, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT, size=size, weight=weight)


def mode_color(pair: tuple[str, str]) -> str:
    """Pick one colour of a (light, dark) pair for plain tk widgets like Canvas."""
    return pair[1] if ctk.get_appearance_mode() == "Dark" else pair[0]


# Topic name keywords -> Lucide icon name.
TOPIC_ICONS = [
    (("data", "statistic", "analytics", "machine learning"), "chart-column"),
    (("interview",), "handshake"),
    (("present", "meeting"), "presentation"),
    (("work", "career", "office", "job", "business"), "briefcase"),
    (("tech", "ai", "computer", "software"), "cpu"),
    (("food", "cook", "restaurant"), "utensils"),
    (("travel", "trip", "holiday"), "plane"),
    (("health", "fitness", "sport", "exercise"), "heart-pulse"),
    (("study", "education", "university", "school", "learn"), "graduation-cap"),
    (("opinion", "debate", "society"), "message-circle"),
    (("story", "experience", "memory"), "book-open"),
    (("money", "shopping", "finance"), "shopping-bag"),
    (("environment", "nature", "climate"), "leaf"),
    (("people", "friend", "family", "social"), "users"),
    (("daily", "life", "home", "hobby"), "coffee"),
    (("idea", "creative"), "lightbulb"),
]


def topic_icon(topic: str) -> str:
    low = topic.lower()
    for words, icon_name in TOPIC_ICONS:
        if any(re.search(rf"\b{re.escape(w)}", low) for w in words):
            return icon_name
    return "message-square"


@lru_cache(maxsize=512)
def _tinted(name: str, color: str) -> Image.Image:
    base = Image.open(paths.asset("icons", f"{name}.png")).convert("RGBA")
    solid = Image.new("RGBA", base.size, color)
    solid.putalpha(base.getchannel("A"))
    return solid


def icon(name: str, size: int = 20, color: tuple[str, str] = INK) -> ctk.CTkImage:
    return ctk.CTkImage(light_image=_tinted(name, color[0]),
                        dark_image=_tinted(name, color[1]), size=(size, size))


WHITE = ("#FFFFFF", "#FFFFFF")

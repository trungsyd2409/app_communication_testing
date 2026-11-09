"""Questions, practice history and settings, stored as JSON files in the data folder."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from . import paths

MIN_MINUTES = 1.0
MAX_MINUTES = 10.0

# Column order used for CSV export and the Google Sheet template.
CSV_COLUMNS = [
    "id", "topic", "question", "reference_answer", "key_phrases",
    "difficulty", "min_minutes", "max_minutes", "tags",
]

# Accepted header spellings -> internal field name.
HEADER_ALIASES = {
    "id": "id",
    "topic": "topic", "category": "topic", "field": "topic",
    "question": "question", "prompt": "question",
    "reference_answer": "reference_answer", "answer": "reference_answer",
    "reference": "reference_answer", "sample_answer": "reference_answer",
    "model_answer": "reference_answer",
    "key_phrases": "key_phrases", "phrases": "key_phrases",
    "vocabulary": "key_phrases", "keywords": "key_phrases",
    "difficulty": "difficulty", "level": "difficulty",
    "min_minutes": "min_minutes", "min": "min_minutes", "min_time": "min_minutes",
    "max_minutes": "max_minutes", "max": "max_minutes", "max_time": "max_minutes",
    "tags": "tags",
}

DEFAULT_SETTINGS = {
    "sheet_url": "",
    "sync_mode": "link",          # "link" (shared link, no login) or "google" (sign in)
    "auto_sync": True,
    "last_sync": "",
    "last_sync_count": 0,
    "time_mode": "random",        # "random" = 1-10 min, "quick" = 1-3 min
    "record_audio": True,
    "beep": True,
    "keep_recordings": 60,
    "appearance": "light",
    "selected_topics": [],
    "bag": [],
}


def clamp_minutes(value: float) -> float:
    return max(MIN_MINUTES, min(MAX_MINUTES, value))


def _to_float(value, default: float) -> float:
    try:
        text = str(value).strip().replace(",", ".")
        return float(text) if text else default
    except (TypeError, ValueError):
        return default


def split_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value or "")
    for sep in ("|", "\n"):
        text = text.replace(sep, ";")
    return [part.strip() for part in text.split(";") if part.strip()]


def stable_id(topic: str, question: str) -> str:
    raw = f"{topic.strip().lower()}|{question.strip().lower()}"
    return "q" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


@dataclass
class Question:
    id: str
    topic: str
    question: str
    reference_answer: str = ""
    key_phrases: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    min_minutes: float = MIN_MINUTES
    max_minutes: float = MAX_MINUTES
    tags: list[str] = field(default_factory=list)
    source: str = "local"         # "local", "drive" or "starter"
    updated: str = ""

    @classmethod
    def from_dict(cls, data: dict, source: str | None = None) -> "Question | None":
        question = str(data.get("question", "")).strip()
        if not question:
            return None
        topic = str(data.get("topic", "")).strip() or "General"
        lo = clamp_minutes(_to_float(data.get("min_minutes"), MIN_MINUTES))
        hi = clamp_minutes(_to_float(data.get("max_minutes"), MAX_MINUTES))
        if lo > hi:
            lo, hi = hi, lo
        difficulty = str(data.get("difficulty", "medium")).strip().lower() or "medium"
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"
        return cls(
            id=str(data.get("id", "")).strip() or stable_id(topic, question),
            topic=topic,
            question=question,
            reference_answer=str(data.get("reference_answer", "")).strip(),
            key_phrases=split_list(data.get("key_phrases", "")),
            difficulty=difficulty,
            min_minutes=lo,
            max_minutes=hi,
            tags=split_list(data.get("tags", "")),
            source=source or str(data.get("source", "local")),
            updated=str(data.get("updated", "")),
        )

    def to_csv_row(self) -> dict:
        row = asdict(self)
        row["key_phrases"] = "; ".join(self.key_phrases)
        row["tags"] = "; ".join(self.tags)
        row["min_minutes"] = f"{self.min_minutes:g}"
        row["max_minutes"] = f"{self.max_minutes:g}"
        return {key: row[key] for key in CSV_COLUMNS}


def normalise_header(name: str) -> str:
    key = str(name or "").strip().lower().replace(" ", "_").replace("-", "_")
    return HEADER_ALIASES.get(key, key)


def parse_csv_text(text: str, source: str) -> list[Question]:
    """Parse CSV text (from a file or a Google Sheet export) into questions."""
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    headers = [normalise_header(h) for h in rows[0]]
    if "question" not in headers:
        raise ValueError(
            "The sheet needs a header row with at least a 'question' column "
            "(and ideally 'topic' and 'reference_answer')."
        )
    seen: set[str] = set()
    result: list[Question] = []
    for raw in rows[1:]:
        data = {headers[i]: raw[i] for i in range(min(len(headers), len(raw)))}
        q = Question.from_dict(data, source=source)
        if q is None:
            continue
        if q.id in seen:            # duplicate ids in the sheet: make them unique
            q.id = f"{q.id}_{len(result)}"
        seen.add(q.id)
        result.append(q)
    return result


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        backup = path.with_suffix(path.suffix + ".broken")
        try:
            shutil.copy(path, backup)
        except OSError:
            pass
        return default


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


class Store:
    """All persistent state of the app."""

    def __init__(self, folder: Path | None = None):
        self.folder = folder or paths.data_dir()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.q_path = self.folder / "questions.json"
        self.h_path = self.folder / "history.json"
        self.s_path = self.folder / "settings.json"

        # data/default_settings.json (bundled) can preset e.g. the sheet link for a build.
        bundled = _read_json(paths.resource_dir() / "data" / "default_settings.json", {})
        self.settings: dict = {**DEFAULT_SETTINGS, **bundled, **_read_json(self.s_path, {})}
        self.history: list[dict] = _read_json(self.h_path, [])
        raw_questions = _read_json(self.q_path, None)
        if raw_questions is None:
            self.questions = self._load_starter()
            self.save_questions()
        else:
            self.questions = [q for q in (Question.from_dict(d) for d in raw_questions) if q]

    # ------------------------------------------------------------------ files
    def _load_starter(self) -> list[Question]:
        path = paths.resource_dir() / "data" / "starter_questions.csv"
        try:
            return parse_csv_text(path.read_text(encoding="utf-8"), source="starter")
        except (OSError, ValueError):
            return []

    def save_questions(self) -> None:
        _write_json(self.q_path, [asdict(q) for q in self.questions])

    def save_history(self) -> None:
        _write_json(self.h_path, self.history)

    def save_settings(self) -> None:
        _write_json(self.s_path, self.settings)

    # -------------------------------------------------------------- questions
    def get(self, qid: str) -> Question | None:
        return next((q for q in self.questions if q.id == qid), None)

    def topics(self) -> list[str]:
        return sorted({q.topic for q in self.questions}, key=str.lower)

    def upsert(self, q: Question) -> None:
        q.updated = datetime.now().isoformat(timespec="seconds")
        if q.source == "starter":
            q.source = "local"
        for i, old in enumerate(self.questions):
            if old.id == q.id:
                self.questions[i] = q
                break
        else:
            self.questions.append(q)
        self.save_questions()

    def new_id(self) -> str:
        return "l" + uuid.uuid4().hex[:10]

    def delete(self, qid: str) -> None:
        self.questions = [q for q in self.questions if q.id != qid]
        self.save_questions()

    def replace_drive_questions(self, fetched: list[Question]) -> int:
        """Sheet is the source of truth: drop old sheet + starter questions, keep local ones."""
        fetched_ids = {q.id for q in fetched}
        local = [q for q in self.questions
                 if q.source == "local" and q.id not in fetched_ids]
        for q in fetched:
            q.source = "drive"
        self.questions = fetched + local
        self.save_questions()
        return len(fetched)

    def import_csv(self, path: Path) -> int:
        imported = parse_csv_text(path.read_text(encoding="utf-8-sig"), source="local")
        existing = {q.id: i for i, q in enumerate(self.questions)}
        for q in imported:
            if q.id in existing and self.questions[existing[q.id]].source == "drive":
                q.id = self.new_id()
            if q.id in existing:
                self.questions[existing[q.id]] = q
            else:
                self.questions.append(q)
        self.save_questions()
        return len(imported)

    def export_csv(self, path: Path, questions: Iterable[Question] | None = None) -> int:
        items = list(questions if questions is not None else self.questions)
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for q in items:
                writer.writerow(q.to_csv_row())
        return len(items)

    # ---------------------------------------------------------------- history
    def add_session(self, entry: dict) -> None:
        self.history.append(entry)
        self.save_history()
        self.cleanup_recordings()

    def last_rating(self, qid: str) -> int | None:
        for entry in reversed(self.history):
            if entry.get("question_id") == qid and entry.get("rating"):
                return int(entry["rating"])
        return None

    def cleanup_recordings(self) -> None:
        keep = int(self.settings.get("keep_recordings", 60) or 0)
        if keep <= 0:
            return
        files = sorted(paths.recordings_dir().glob("*.wav"), key=lambda p: p.stat().st_mtime)
        for old in files[:-keep]:
            try:
                old.unlink()
            except OSError:
                pass

    def stats(self, today: date | None = None) -> dict:
        today = today or date.today()
        per_day: dict[date, float] = {}
        ratings = []
        for entry in self.history:
            try:
                day = datetime.fromisoformat(entry["finished_at"]).date()
            except (KeyError, ValueError):
                continue
            per_day[day] = per_day.get(day, 0.0) + float(entry.get("spoken_seconds", 0)) / 60
            if entry.get("rating"):
                ratings.append(int(entry["rating"]))

        streak = 0
        cursor = today if today in per_day else today - timedelta(days=1)
        while cursor in per_day:
            streak += 1
            cursor -= timedelta(days=1)

        last_14 = [(today - timedelta(days=i), per_day.get(today - timedelta(days=i), 0.0))
                   for i in range(13, -1, -1)]
        return {
            "today_minutes": per_day.get(today, 0.0),
            "streak": streak,
            "sessions": len(self.history),
            "total_minutes": sum(per_day.values()),
            "avg_rating": (sum(ratings) / len(ratings)) if ratings else None,
            "last_14": last_14,
        }

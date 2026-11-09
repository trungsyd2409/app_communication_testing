"""Choose the next question and a random speaking time."""
from __future__ import annotations

import random

from .storage import MAX_MINUTES, MIN_MINUTES, Question, Store

QUICK_MAX = 3.0
STEP = 0.5   # minutes


def candidates(store: Store, topics: list[str] | None = None) -> list[Question]:
    chosen = set(topics or [])
    return [q for q in store.questions if not chosen or q.topic in chosen]


def _weight(store: Store, q: Question) -> float:
    rating = store.last_rating(q.id)
    if rating is None:
        return 3.0
    return {1: 8.0, 2: 5.0, 3: 3.0, 4: 2.0, 5: 1.0}.get(rating, 3.0)


def next_question(store: Store, topics: list[str] | None = None,
                  exclude: str | None = None, rng: random.Random | None = None) -> Question | None:
    """Shuffle bag: no repeats until every matching question has appeared.

    Inside the bag, questions you rated low have a higher chance to come first.
    """
    rng = rng or random.Random()
    pool = candidates(store, topics)
    if not pool:
        return None
    by_id = {q.id: q for q in pool}
    bag = [qid for qid in store.settings.get("bag", []) if qid in by_id]
    if not bag or (len(bag) == 1 and bag[0] == exclude and len(pool) > 1):
        bag = list(by_id)
        rng.shuffle(bag)

    options = [qid for qid in bag if qid != exclude] or bag
    weights = [_weight(store, by_id[qid]) for qid in options]
    pick = rng.choices(options, weights=weights, k=1)[0]
    bag.remove(pick)
    store.settings["bag"] = bag
    store.save_settings()
    return by_id[pick]


def random_minutes(q: Question | None, mode: str = "random",
                   rng: random.Random | None = None) -> float:
    """Random time in half-minute steps, always between 1 and 10 minutes."""
    rng = rng or random.Random()
    lo = max(MIN_MINUTES, q.min_minutes if q else MIN_MINUTES)
    hi = min(MAX_MINUTES, q.max_minutes if q else MAX_MINUTES)
    if mode == "quick":
        hi = min(hi, QUICK_MAX)
        lo = min(lo, hi)
    if lo > hi:
        lo, hi = MIN_MINUTES, MAX_MINUTES
    steps = int(round((hi - lo) / STEP))
    return lo + STEP * rng.randint(0, steps)


def format_minutes(minutes: float) -> str:
    whole = int(minutes)
    if minutes - whole >= 0.5:
        return f"{whole}m 30s" if whole else "30s"
    return f"{whole} min"

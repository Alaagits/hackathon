"""Stage 3: Score executives by public exposure / deepfake-target attractiveness."""

import sqlite3
from db.database import set_exposure_score

# Higher = more likely deepfake target
_TITLE_SCORES: dict[str, int] = {
    "ceo": 100,
    "chief executive": 100,
    "president": 95,
    "founder": 90,
    "co-founder": 90,
    "cfo": 88,
    "chief financial": 88,
    "cto": 88,
    "chief technology": 88,
    "coo": 85,
    "chief operating": 85,
    "cmo": 83,
    "chief marketing": 83,
    "ciso": 82,
    "chief information security": 82,
    "evp": 75,
    "executive vice president": 75,
    "svp": 70,
    "senior vice president": 70,
    "vp": 60,
    "vice president": 60,
    "director": 50,
    "head of": 45,
    "manager": 35,
}


def _title_score(title: str) -> int:
    if not title:
        return 30
    tl = title.lower()
    for keyword, score in _TITLE_SCORES.items():
        if keyword in tl:
            return score
    return 30


def prioritize_persons(
    db: sqlite3.Connection,
    persons: list[dict],
    top_n: int,
) -> list[dict]:
    for p in persons:
        score = _title_score(p.get("title") or "")
        p["exposure_score"] = score
        set_exposure_score(db, p["id"], score)

    ranked = sorted(persons, key=lambda x: x["exposure_score"], reverse=True)
    return ranked[:top_n]

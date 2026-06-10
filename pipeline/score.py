"""Stage 5: Multi-signal deepfake risk scoring."""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from tqdm import tqdm

from db.database import (
    get_baseline_videos,
    get_candidate_videos,
    insert_score,
)

SUSPICIOUS_KEYWORDS = {
    "deepfake", "fake news", "ai generated", "ai-generated", "synthetic voice",
    "voice clone", "face swap", "exposed", "shocking", "leaked", "viral",
    "you won't believe", "watch before deleted", "urgent message",
    "breaking news exclusive", "hidden camera",
}


# ---------------------------------------------------------------------------
# Sub-scorers
# ---------------------------------------------------------------------------

def _days_since(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except (ValueError, TypeError):
        return None


def _score_source_credibility(video: dict) -> tuple[int, list[str]]:
    """0-30 pts. Measures how suspicious the channel/source is."""
    score = 0
    notes: list[str] = []

    channel_age = _days_since(video["channel_created_at"])
    if channel_age is not None:
        if channel_age < 30:
            score += 25
            notes.append(f"channel only {channel_age}d old")
        elif channel_age < 90:
            score += 15
            notes.append(f"channel {channel_age}d old")
        elif channel_age < 180:
            score += 5

    title_lower = (video["title"] or "").lower()
    desc_lower = (video["description"] or "").lower()
    hits = [kw for kw in SUSPICIOUS_KEYWORDS if kw in title_lower or kw in desc_lower]
    if hits:
        score += 10
        notes.append(f"suspicious keywords: {', '.join(hits[:3])}")

    score = min(score, 30)

    # Verified/official channels are capped at 15 regardless
    if video["channel_verified"]:
        if score > 15:
            score = 15
        notes.append("channel verified (capped at 15)")

    return score, notes


def _score_upload_recency(video: dict) -> tuple[int, list[str]]:
    """0-20 pts. Very recent uploads are higher risk when combined with other signals."""
    age = _days_since(video["published_at"])
    if age is None:
        return 0, []
    if age < 1:
        return 20, ["uploaded today"]
    if age < 7:
        return 16, [f"uploaded {age}d ago"]
    if age < 30:
        return 10, [f"uploaded {age}d ago"]
    if age < 90:
        return 5, []
    return 0, []


def _score_metadata(video: dict) -> tuple[int, list[str]]:
    """0-20 pts. Gaps in metadata suggest low-effort or automated upload."""
    score = 0
    notes: list[str] = []

    if not (video["description"] or "").strip():
        score += 5
        notes.append("no description")

    if not (video["tags"] or "").strip():
        score += 5
        notes.append("no tags")

    views = video["view_count"] or 0
    subs = video["channel_subscriber_count"] or 0
    if subs and views and views > subs * 10:
        score += 10
        notes.append(f"view/sub anomaly ({views:,} views, {subs:,} subs)")

    return min(score, 20), notes


def _score_voice_match(
    candidate_video_id: int,
    candidate_audio: Optional[str],
    baseline_embeddings: list[str],
) -> tuple[int, list[str], Optional[float]]:
    """0-30 pts. Low voice similarity → high suspicion."""
    if not candidate_audio or not baseline_embeddings:
        return 0, [], None

    try:
        import numpy as np
        from resemblyzer import VoiceEncoder, preprocess_wav
        from pathlib import Path

        candidate_wav = preprocess_wav(Path(candidate_audio))
        encoder = VoiceEncoder()
        cand_emb = encoder.embed_utterance(candidate_wav)

        # Average similarity across all baselines
        sims = []
        for emb_path in baseline_embeddings:
            if not os.path.exists(emb_path):
                continue
            baseline_emb = np.load(emb_path)
            sim = float(np.dot(cand_emb, baseline_emb))
            sims.append(sim)

        if not sims:
            return 0, [], None

        avg_sim = sum(sims) / len(sims)
        note = f"voice similarity {avg_sim:.3f}"

        if avg_sim < 0.50:
            return 30, [note], avg_sim
        if avg_sim < 0.65:
            return 20, [note], avg_sim
        if avg_sim < 0.75:
            return 10, [note], avg_sim
        return 0, [note], avg_sim

    except ImportError:
        return 0, [], None
    except Exception as exc:
        print(f"      [score] Voice match error (vid {candidate_video_id}): {exc}")
        return 0, [], None


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def _risk_level(total: int) -> str:
    if total >= 70:
        return "high"
    if total >= 45:
        return "medium"
    if total >= 20:
        return "low"
    return "unverified"


_RISK_EMOJI = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
    "unverified": "⚪",
}


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def score_candidates(
    db: sqlite3.Connection,
    persons: list[dict],
    skip_voice: bool = False,
) -> list[dict]:
    """Score all candidate videos for each person. Returns a flat list of result dicts."""
    all_results: list[dict] = []

    for person in tqdm(persons, desc="Scoring", unit="person"):
        person_id = person["id"]

        # Build baseline embedding list for this person
        baseline_emb_paths: list[str] = []
        if not skip_voice:
            for bv in get_baseline_videos(db, person_id):
                if bv["embedding_path"] and os.path.exists(bv["embedding_path"]):
                    baseline_emb_paths.append(bv["embedding_path"])

        candidates = get_candidate_videos(db, person_id)
        if not candidates:
            continue

        for cand in candidates:
            cand = dict(cand)

            sc_score, sc_notes = _score_source_credibility(cand)
            aa_score, aa_notes = _score_upload_recency(cand)
            md_score, md_notes = _score_metadata(cand)

            vm_score, vm_notes, voice_sim = (0, [], None)
            if not skip_voice:
                vm_score, vm_notes, voice_sim = _score_voice_match(
                    cand["id"],
                    cand.get("audio_path"),
                    baseline_emb_paths,
                )

            total = sc_score + aa_score + md_score + vm_score
            level = _risk_level(total)

            all_notes = sc_notes + aa_notes + md_notes + vm_notes
            notes_str = "; ".join(all_notes)

            insert_score(
                db,
                candidate_video_id=cand["id"],
                person_id=person_id,
                source_credibility=sc_score,
                account_age=aa_score,
                metadata=md_score,
                voice_match=vm_score,
                total=total,
                risk_level=level,
                voice_similarity=voice_sim,
                notes=notes_str,
            )

            emoji = _RISK_EMOJI.get(level, "⚪")
            all_results.append({
                "person_id": person_id,
                "person_name": person["name"],
                "person_title": person.get("title", ""),
                "video_id": cand["video_id"],
                "title": cand["title"],
                "channel_name": cand["channel_name"],
                "channel_verified": bool(cand["channel_verified"]),
                "published_at": cand["published_at"],
                "view_count": cand["view_count"],
                "source_credibility_score": sc_score,
                "account_age_score": aa_score,
                "metadata_score": md_score,
                "voice_match_score": vm_score,
                "total_score": total,
                "risk_level": level,
                "risk_emoji": emoji,
                "voice_similarity": voice_sim,
                "notes": notes_str,
                "url": f"https://www.youtube.com/watch?v={cand['video_id']}",
            })

            if level in ("high", "medium"):
                print(
                    f"      {emoji} [{level.upper()}] {cand['title'][:60]} "
                    f"(score={total})"
                )

    all_results.sort(key=lambda x: x["total_score"], reverse=True)
    return all_results

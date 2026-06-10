"""Stage 4a: Collect known-real video clips to use as voice ground truth."""

import os
import json
import sqlite3
import subprocess
from typing import Optional

from googleapiclient.discovery import build
from tqdm import tqdm

from db.database import upsert_baseline_video, set_baseline_audio

_AUDIO_DIR = os.path.join("data", "audio", "baseline")

# Keywords that suggest an official/authoritative upload
_OFFICIAL_HINTS = {
    "official", "keynote", "conference", "interview", "ted talk", "earnings",
    "annual meeting", "shareholder", "summit", "fireside", "panel",
}


def collect_baseline(
    db: sqlite3.Connection,
    persons: list[dict],
    youtube_key: str,
    skip_download: bool = False,
) -> None:
    os.makedirs(_AUDIO_DIR, exist_ok=True)
    youtube = build("youtube", "v3", developerKey=youtube_key)

    for person in tqdm(persons, desc="Baseline", unit="person"):
        videos = _search_official_videos(youtube, person)
        if not videos:
            print(f"      [{person['name']}] No baseline videos found.")
            continue

        for v in videos[:5]:
            vid_id = upsert_baseline_video(
                db,
                person_id=person["id"],
                video_id=v["video_id"],
                title=v["title"],
                channel_id=v["channel_id"],
                channel_name=v["channel_name"],
                published_at=v["published_at"],
            )

            if skip_download:
                continue

            audio_path = _download_audio(v["video_id"], _AUDIO_DIR)
            embedding_path = None

            if audio_path:
                embedding_path = _compute_embedding(audio_path, v["video_id"])

            set_baseline_audio(db, v["video_id"], audio_path, embedding_path)


def _search_official_videos(youtube, person: dict) -> list[dict]:
    name = person["name"]
    company = person["company"]
    query = f'"{name}" "{company}"'

    try:
        search_resp = (
            youtube.search()
            .list(
                part="snippet",
                q=query,
                type="video",
                maxResults=20,
                order="relevance",
                videoEmbeddable="true",
            )
            .execute()
        )
    except Exception as exc:
        print(f"      [baseline] YouTube search error: {exc}")
        return []

    video_ids = [
        item["id"]["videoId"]
        for item in search_resp.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if not video_ids:
        return []

    # Fetch full video details
    try:
        detail_resp = (
            youtube.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
            .execute()
        )
    except Exception as exc:
        print(f"      [baseline] Video detail fetch error: {exc}")
        return []

    # Prefer videos from verified/official-looking channels
    scored = []
    for item in detail_resp.get("items", []):
        snippet = item.get("snippet", {})
        channel_name_lower = snippet.get("channelTitle", "").lower()
        title_lower = snippet.get("title", "").lower()
        official_hits = sum(1 for h in _OFFICIAL_HINTS if h in title_lower or h in channel_name_lower)
        scored.append((official_hits, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for _, item in scored:
        snippet = item.get("snippet", {})
        results.append({
            "video_id": item["id"],
            "title": snippet.get("title", ""),
            "channel_id": snippet.get("channelId", ""),
            "channel_name": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
        })
    return results


def _download_audio(video_id: str, output_dir: str) -> Optional[str]:
    out_path = os.path.join(output_dir, f"{video_id}.wav")
    if os.path.exists(out_path):
        return out_path

    url = f"https://www.youtube.com/watch?v={video_id}"
    template = os.path.join(output_dir, f"{video_id}.%(ext)s")
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--audio-quality", "5",
        "--no-playlist",
        "-o", template,
        "--quiet", "--no-warnings",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0 and os.path.exists(out_path):
            return out_path
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        if isinstance(exc, FileNotFoundError):
            print("      [baseline] yt-dlp not found — skipping audio download.")
    return None


def _compute_embedding(audio_path: str, video_id: str) -> Optional[str]:
    emb_path = audio_path.replace(".wav", ".npy")
    if os.path.exists(emb_path):
        return emb_path
    try:
        import numpy as np
        from resemblyzer import VoiceEncoder, preprocess_wav
        from pathlib import Path

        wav = preprocess_wav(Path(audio_path))
        encoder = VoiceEncoder()
        embedding = encoder.embed_utterance(wav)
        np.save(emb_path, embedding)
        return emb_path
    except ImportError:
        return None
    except Exception as exc:
        print(f"      [baseline] Embedding error for {video_id}: {exc}")
        return None

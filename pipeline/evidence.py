"""Stage 4b: Collect candidate videos that mention each executive."""

import os
import sqlite3
import subprocess
from typing import Optional

from googleapiclient.discovery import build
from tqdm import tqdm

from db.database import upsert_candidate_video, set_candidate_audio

_AUDIO_DIR = os.path.join("data", "audio", "candidates")

# Videos whose channel is one of these will be de-prioritised as candidates
# (large verified news channels rarely host deepfakes)
_TRUSTED_CHANNEL_KEYWORDS = {
    "cnbc", "bloomberg", "reuters", "bbc", "cnn", "fox news", "nbc news",
    "abc news", "cbs news", "the wall street journal", "wsj", "techcrunch",
    "forbes", "wired", "the verge", "associated press",
}


def collect_evidence(
    db: sqlite3.Connection,
    persons: list[dict],
    youtube_key: str,
    skip_download: bool = False,
) -> None:
    os.makedirs(_AUDIO_DIR, exist_ok=True)
    youtube = build("youtube", "v3", developerKey=youtube_key)

    for person in tqdm(persons, desc="Evidence", unit="person"):
        videos = _search_candidate_videos(youtube, person)
        if not videos:
            print(f"      [{person['name']}] No candidate videos found.")
            continue

        for v in videos:
            vid_id = upsert_candidate_video(
                db,
                person_id=person["id"],
                video_id=v["video_id"],
                title=v["title"],
                channel_id=v["channel_id"],
                channel_name=v["channel_name"],
                channel_created_at=v.get("channel_created_at"),
                channel_subscriber_count=v.get("channel_subscriber_count"),
                channel_verified=v.get("channel_verified", False),
                published_at=v["published_at"],
                view_count=v.get("view_count"),
                like_count=v.get("like_count"),
                description=v.get("description"),
                tags=v.get("tags"),
                duration=v.get("duration"),
            )

            if skip_download:
                continue

            audio_path = _download_audio(v["video_id"], _AUDIO_DIR)
            if audio_path:
                set_candidate_audio(db, v["video_id"], audio_path)


def _search_candidate_videos(youtube, person: dict) -> list[dict]:
    name = person["name"]
    query = f'"{name}"'

    try:
        search_resp = (
            youtube.search()
            .list(
                part="snippet",
                q=query,
                type="video",
                maxResults=25,
                order="date",          # most recent first — freshness is a risk signal
                videoEmbeddable="true",
            )
            .execute()
        )
    except Exception as exc:
        print(f"      [evidence] YouTube search error: {exc}")
        return []

    video_ids = [
        item["id"]["videoId"]
        for item in search_resp.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    channel_ids = list({
        item["snippet"]["channelId"]
        for item in search_resp.get("items", [])
        if item.get("snippet", {}).get("channelId")
    })

    if not video_ids:
        return []

    # Fetch video details
    try:
        video_resp = (
            youtube.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
            .execute()
        )
    except Exception as exc:
        print(f"      [evidence] Video detail fetch error: {exc}")
        return []

    # Fetch channel details for all involved channels
    channel_meta: dict[str, dict] = {}
    if channel_ids:
        try:
            ch_resp = (
                youtube.channels()
                .list(part="snippet,statistics,status", id=",".join(channel_ids[:50]))
                .execute()
            )
            for ch in ch_resp.get("items", []):
                channel_meta[ch["id"]] = {
                    "channel_created_at": ch["snippet"].get("publishedAt"),
                    "channel_subscriber_count": int(
                        ch.get("statistics", {}).get("subscriberCount") or 0
                    ),
                    "channel_verified": bool(
                        ch.get("status", {}).get("isLinked")
                        or _looks_official(ch["snippet"].get("title", ""))
                    ),
                }
        except Exception as exc:
            print(f"      [evidence] Channel detail fetch error: {exc}")

    results = []
    for item in video_resp.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        channel_id = snippet.get("channelId", "")
        channel_name = snippet.get("channelTitle", "")
        ch = channel_meta.get(channel_id, {})

        tags_list = snippet.get("tags", []) or []

        results.append({
            "video_id": item["id"],
            "title": snippet.get("title", ""),
            "channel_id": channel_id,
            "channel_name": channel_name,
            "channel_created_at": ch.get("channel_created_at"),
            "channel_subscriber_count": ch.get("channel_subscriber_count"),
            "channel_verified": ch.get("channel_verified", False),
            "published_at": snippet.get("publishedAt", ""),
            "view_count": int(stats.get("viewCount") or 0),
            "like_count": int(stats.get("likeCount") or 0),
            "description": snippet.get("description", ""),
            "tags": ",".join(tags_list),
            "duration": item.get("contentDetails", {}).get("duration", ""),
        })

    return results


def _looks_official(channel_name: str) -> bool:
    name_lower = channel_name.lower()
    return any(k in name_lower for k in _TRUSTED_CHANNEL_KEYWORDS)


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
    except FileNotFoundError:
        print("      [evidence] yt-dlp not found — skipping audio download.")
    except subprocess.TimeoutExpired:
        pass
    return None

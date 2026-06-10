def analyze_audio(file_path: str, content_type: str) -> dict:
    if content_type != "video":
        return {
            "audio_checked": False,
            "audio_score": 0,
            "label": "not_applicable",
            "explanation": "Audio analysis is only relevant for video files.",
        }

    return {
        "audio_checked": True,
        "audio_score": 50,
        "label": "medium_suspicion",
        "explanation": (
            "Audio analysis placeholder. "
            "Future version will check voice match and lip-sync consistency."
        ),
    }

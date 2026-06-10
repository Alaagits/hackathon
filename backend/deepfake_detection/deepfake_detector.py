def detect_deepfake(file_path: str, content_type: str) -> dict:
    if content_type == "image":
        return _analyze_image(file_path)
    if content_type == "video":
        return _analyze_video(file_path)
    return {
        "deepfake_score": 0,
        "label": "unsupported",
        "explanation": "Unsupported media type.",
    }


def _analyze_image(file_path: str) -> dict:
    return {
        "deepfake_score": 45,
        "label": "medium_suspicion",
        "explanation": (
            "Image analysis placeholder. "
            "Replace with real model output (e.g. Hugging Face deepfake classifier)."
        ),
    }


def _analyze_video(file_path: str) -> dict:
    return {
        "deepfake_score": 55,
        "label": "medium_suspicion",
        "explanation": (
            "Video analysis placeholder. "
            "Replace with frame-based model output."
        ),
    }

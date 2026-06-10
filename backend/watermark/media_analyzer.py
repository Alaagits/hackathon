import mimetypes

from watermark.metadata_checker import check_metadata
from watermark.synthid_checker import check_synthid_placeholder
from watermark.c2pa_checker import check_c2pa_placeholder


def analyze_watermark(file_path: str) -> dict:
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type is None:
        return {"status": "error", "message": "Unknown file type"}

    if mime_type.startswith("image"):
        content_type = "image"
    elif mime_type.startswith("video"):
        content_type = "video"
    else:
        return {"status": "error", "message": "Unsupported file type"}

    metadata_result = check_metadata(file_path, content_type)
    synthid_result = check_synthid_placeholder()
    c2pa_result = check_c2pa_placeholder()
    watermark_score = _calculate_score(metadata_result, synthid_result, c2pa_result)

    return {
        "status": "success",
        "content_type": content_type,
        "mime_type": mime_type,
        "metadata": metadata_result,
        "c2pa": c2pa_result,
        "synthid": synthid_result,
        "watermark_score": watermark_score,
        "risk_level": _get_risk_level(watermark_score),
        "summary": (
            "Metadata, C2PA, and SynthID checks completed. "
            "No watermark alone can prove whether content is real or fake. "
            "This module should be combined with face verification and deepfake detection."
        ),
    }


def _calculate_score(metadata_result: dict, synthid_result: dict, c2pa_result: dict) -> int:
    score = 0
    if not metadata_result.get("metadata_found"):
        score += 20
    if not c2pa_result.get("c2pa_found"):
        score += 10
    if synthid_result.get("status") == "detected":
        score += 80
    return min(score, 100)


def _get_risk_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"

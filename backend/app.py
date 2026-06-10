"""Harel Deepfake Protection — FastAPI backend."""

import mimetypes
import os
import shutil
import sys

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Make sure sibling modules are importable when running from inside backend/
sys.path.insert(0, os.path.dirname(__file__))

from face_match.face_matcher import match_face
from deepfake_detection.deepfake_detector import detect_deepfake
from watermark.media_analyzer import analyze_watermark
from audio_analysis.audio_checker import analyze_audio
from risk_engine import calculate_final_risk

app = FastAPI(title="Harel Deepfake Protection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _detect_content_type(file_path: str) -> tuple[str, str | None]:
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        return "unknown", None
    if mime_type.startswith("image"):
        return "image", mime_type
    if mime_type.startswith("video"):
        return "video", mime_type
    return "unsupported", mime_type


@app.get("/")
def home():
    return {
        "message": "Harel Deepfake Protection backend is running.",
        "endpoint": "POST /analyze-media",
        "docs": "/docs",
    }


@app.post("/analyze-media")
async def analyze_media(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    content_type, mime_type = _detect_content_type(file_path)

    if content_type in ("unknown", "unsupported"):
        return {
            "status": "error",
            "message": "Unsupported or unknown file type.",
            "mime_type": mime_type,
        }

    face_result      = match_face(file_path)
    deepfake_result  = detect_deepfake(file_path, content_type)
    watermark_result = analyze_watermark(file_path)
    audio_result     = analyze_audio(file_path, content_type)

    final_risk = calculate_final_risk(
        face_result, deepfake_result, watermark_result, audio_result
    )

    return {
        "status": "success",
        "content_type": content_type,
        "mime_type": mime_type,
        "face_match": face_result,
        "deepfake_detection": deepfake_result,
        "watermark_check": watermark_result,
        "audio_analysis": audio_result,
        "final_risk": final_risk,
    }

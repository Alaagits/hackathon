import os
from PIL import Image
import cv2


def check_metadata(file_path: str, content_type: str) -> dict:
    if content_type == "image":
        return _check_image_metadata(file_path)
    if content_type == "video":
        return _check_video_metadata(file_path)
    return {"metadata_found": False, "error": "Unsupported content type"}


def _check_image_metadata(file_path: str) -> dict:
    try:
        image = Image.open(file_path)
        exif_data = image.getexif()
        return {
            "metadata_found": len(exif_data) > 0,
            "format": image.format,
            "size": image.size,
            "exif_count": len(exif_data),
            "file_size_kb": round(os.path.getsize(file_path) / 1024, 2),
        }
    except Exception as exc:
        return {"metadata_found": False, "error": str(exc)}


def _check_video_metadata(file_path: str) -> dict:
    try:
        video = cv2.VideoCapture(file_path)
        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = video.get(cv2.CAP_PROP_FPS)
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video.release()
        return {
            "metadata_found": True,
            "frame_count": frame_count,
            "fps": fps,
            "resolution": f"{width}x{height}",
            "file_size_kb": round(os.path.getsize(file_path) / 1024, 2),
        }
    except Exception as exc:
        return {"metadata_found": False, "error": str(exc)}

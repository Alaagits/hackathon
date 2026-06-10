import os
import mimetypes

EMPLOYEES_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "employees_db")


def match_face(input_file_path: str) -> dict:
    mime_type, _ = mimetypes.guess_type(input_file_path)
    is_video = mime_type and mime_type.startswith("video")

    if is_video:
        return _match_from_video(input_file_path)
    return _match_from_image(input_file_path)


def _match_from_video(video_path: str) -> dict:
    from video_frame_extractor import extract_frames

    frames = extract_frames(video_path, output_dir="temp_frames", every_n_frames=30)
    if not frames:
        return {"employee_name": None, "face_match_score": 0, "matched": False}

    best = {"employee_name": None, "face_match_score": 0, "matched": False}
    for frame_path in frames[:5]:       # limit to first 5 frames for speed
        result = _match_from_image(frame_path)
        if result["face_match_score"] > best["face_match_score"]:
            best = result
    return best


def _match_from_image(image_path: str) -> dict:
    db_path = os.path.abspath(EMPLOYEES_DB_PATH)

    if not os.path.isdir(db_path) or not os.listdir(db_path):
        return {
            "employee_name": None,
            "face_match_score": 0,
            "matched": False,
            "note": "employees_db is empty — add employee photo folders to enable face matching.",
        }

    try:
        from deepface import DeepFace
    except ImportError:
        return {
            "employee_name": None,
            "face_match_score": 0,
            "matched": False,
            "note": "deepface not installed — run: pip install deepface",
        }

    best = {"employee_name": None, "face_match_score": 0, "matched": False}

    for employee_folder in os.listdir(db_path):
        employee_path = os.path.join(db_path, employee_folder)
        if not os.path.isdir(employee_path):
            continue

        for image_name in os.listdir(employee_path):
            ref_path = os.path.join(employee_path, image_name)
            try:
                result = DeepFace.verify(
                    img1_path=image_path,
                    img2_path=ref_path,
                    enforce_detection=False,
                )
                distance = result.get("distance", 1)
                score = max(0.0, round((1 - distance) * 100, 2))
                if score > best["face_match_score"]:
                    best = {
                        "employee_name": employee_folder,
                        "face_match_score": score,
                        "matched": result.get("verified", False),
                    }
            except Exception:
                continue

    return best

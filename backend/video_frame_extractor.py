import cv2
import os


def extract_frames(
    video_path: str,
    output_dir: str = "temp_frames",
    every_n_frames: int = 30,
) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)

    video = cv2.VideoCapture(video_path)
    frames: list[str] = []
    frame_index = 0
    saved_index = 0

    while True:
        success, frame = video.read()
        if not success:
            break
        if frame_index % every_n_frames == 0:
            frame_path = os.path.join(output_dir, f"frame_{saved_index}.jpg")
            cv2.imwrite(frame_path, frame)
            frames.append(frame_path)
            saved_index += 1
        frame_index += 1

    video.release()
    return frames

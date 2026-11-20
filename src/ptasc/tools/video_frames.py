"""从视频字节里按目标帧率抽出灰度帧。"""

import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".gif"}


def is_video_name(name: str) -> bool:
    return Path(name).suffix.lower() in VIDEO_SUFFIXES


def read_frames(
    data: bytes,
    suffix: str,
    *,
    sample_fps: float,
    max_frames: int,
    max_seconds: float,
    max_edge: int,
) -> tuple[list[Image.Image], float]:
    if sample_fps <= 0 or max_frames < 1 or max_seconds <= 0 or max_edge < 1:
        raise ValueError("视频采样参数必须为正")
    kind = suffix.lower()
    if kind == ".gif":
        return _gif_frames(
            data,
            max_edge,
            sample_fps=sample_fps,
            max_frames=max_frames,
            max_seconds=max_seconds,
        )
    return _capture_frames(
        data,
        kind if kind in VIDEO_SUFFIXES else ".mp4",
        sample_fps=sample_fps,
        max_frames=max_frames,
        max_seconds=max_seconds,
        max_edge=max_edge,
    )


def load_still_frames(blobs: list[bytes], max_edge: int) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for blob in blobs:
        try:
            source = Image.open(BytesIO(blob))
            source.load()
        except OSError as exc:
            raise ValueError("无法读取视频画面") from exc
        frames.append(_limit(source, max_edge))
    if not frames:
        raise ValueError("视频没有画面")
    return frames


def _gif_frames(
    data: bytes,
    max_edge: int,
    *,
    sample_fps: float,
    max_frames: int,
    max_seconds: float,
) -> tuple[list[Image.Image], float]:
    try:
        source = Image.open(BytesIO(data))
    except OSError as exc:
        raise ValueError("无法读取视频") from exc
    count = getattr(source, "n_frames", 1)
    source.seek(0)
    duration = int(source.info.get("duration") or 100) / 1000
    source_fps = 1 / duration if duration else sample_fps
    step, output_fps = _step(source_fps, sample_fps)
    frames: list[Image.Image] = []
    elapsed = 0.0
    for index in range(count):
        if elapsed >= max_seconds:
            break
        source.seek(index)
        frame_duration = int(source.info.get("duration") or 100) / 1000
        if index % step == 0:
            frames.append(_limit(source.convert("L"), max_edge))
            if len(frames) >= max_frames:
                break
        elapsed += frame_duration
    if not frames:
        raise ValueError("视频没有画面")
    return frames, output_fps


def _capture_frames(
    data: bytes,
    suffix: str,
    *,
    sample_fps: float,
    max_frames: int,
    max_seconds: float,
    max_edge: int,
) -> tuple[list[Image.Image], float]:
    import cv2

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / f"source{suffix}"
        path.write_bytes(data)
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise ValueError("无法读取视频")
        source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        if source_fps < 1 or source_fps > 240:
            source_fps = sample_fps
        step, output_fps = _step(source_fps, sample_fps)
        frames: list[Image.Image] = []
        index = 0
        try:
            while index / source_fps < max_seconds:
                if index % step == 0:
                    if not capture.grab():
                        break
                    ok, frame = capture.retrieve()
                    if not ok:
                        break
                    gray = cv2.cvtColor(_shrink(frame, max_edge), cv2.COLOR_BGR2GRAY)
                    frames.append(Image.fromarray(gray))
                    if len(frames) >= max_frames:
                        break
                elif not capture.grab():
                    break
                index += 1
        finally:
            capture.release()
    if not frames:
        raise ValueError("视频没有画面")
    return frames, output_fps


def _step(source_fps: float, sample_fps: float) -> tuple[int, float]:
    output_fps = min(source_fps, sample_fps)
    step = max(1, int(round(source_fps / output_fps)))
    return step, source_fps / step


def _shrink(frame, max_edge: int):
    import cv2

    height, width = frame.shape[:2]
    edge = max(height, width)
    if edge <= max_edge:
        return frame
    scale = max_edge / edge
    size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)


def _limit(image: Image.Image, max_edge: int) -> Image.Image:
    gray = image if image.mode == "L" else image.convert("L")
    if max(gray.size) <= max_edge:
        return gray.copy()
    fitted = gray.copy()
    fitted.thumbnail((max_edge, max_edge), getattr(getattr(Image, "Resampling", Image), "LANCZOS"))
    return fitted


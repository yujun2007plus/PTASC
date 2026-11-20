"""把整段视频转成字符视频，并尽量保留原来的声音。"""

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ptasc.tools.checksum import file_sha256
from ptasc.tools.pixels_to_ascii import pixels_to_ascii
from ptasc.tools.resize_gray import resize_gray
from ptasc.tools.video_frames import _limit, _shrink, _step

_RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


@dataclass(frozen=True)
class FullVideo:
    mp4: bytes
    opening: str
    columns: int
    rows: int
    fps: float
    frame_count: int
    has_audio: bool
    source_sha256: str


def render_full_file(
    source: Path,
    *,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    sample_fps: float,
    max_edge: int,
    cell_px: int,
) -> FullVideo:
    if sample_fps <= 0 or max_edge < 1 or columns < 1:
        raise ValueError("视频采样参数必须为正")
    suffix = source.suffix.lower()
    if suffix == ".gif":
        frames, fps = _gif_frames(source, sample_fps, max_edge)
    else:
        frames, fps = _video_frames(source, sample_fps, max_edge)
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        silent = folder / "silent.mp4"
        stats = _write_silent(frames, silent, fps, columns, char_aspect, ramp, invert, cell_px)
        finished = folder / "ascii.mp4"
        has_audio = _finish(silent, source, finished)
        data = finished.read_bytes() if finished.exists() and finished.stat().st_size else silent.read_bytes()
        if not data:
            raise ValueError("无法写出字符视频")
    return FullVideo(
        mp4=data,
        opening=stats[0],
        columns=stats[1],
        rows=stats[2],
        fps=fps,
        frame_count=stats[3],
        has_audio=has_audio,
        source_sha256=file_sha256(source),
    )


def _gif_frames(path: Path, sample_fps: float, max_edge: int):
    source = Image.open(path)
    count = getattr(source, "n_frames", 1)
    source.seek(0)
    duration = int(source.info.get("duration") or 100) / 1000
    source_fps = 1 / duration if duration else sample_fps
    step, output_fps = _step(source_fps, sample_fps)

    def generate():
        try:
            for index in range(count):
                source.seek(index)
                if index % step == 0:
                    yield _limit(source.convert("L"), max_edge)
        finally:
            source.close()

    return generate(), output_fps


def _video_frames(path: Path, sample_fps: float, max_edge: int):
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("无法读取视频")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    if source_fps < 1 or source_fps > 240:
        source_fps = sample_fps
    step, output_fps = _step(source_fps, sample_fps)
    reported = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    safety = reported + step + 2 if reported > 0 else 1_000_000

    def generate():
        try:
            index = 0
            while index < safety:
                if not capture.grab():
                    break
                if index % step == 0:
                    ok, frame = capture.retrieve()
                    if not ok:
                        break
                    gray = cv2.cvtColor(_shrink(frame, max_edge), cv2.COLOR_BGR2GRAY)
                    yield Image.fromarray(gray)
                index += 1
        finally:
            capture.release()

    return generate(), output_fps


def _write_silent(frames, path: Path, fps: float, columns: int, char_aspect: float, ramp: str, invert: bool, cell_px: int):
    import cv2
    import numpy as np

    from ptasc.tools.ascii_canvas import paint_frame

    pending = iter(frames)
    try:
        first = next(pending)
    except StopIteration as exc:
        raise ValueError("视频没有画面") from exc
    fitted = resize_gray(first if first.mode == "L" else first.convert("L"), columns, char_aspect)
    opening = pixels_to_ascii(fitted, ramp, invert, stretch=False)
    canvas = paint_frame(opening, invert=invert, cell_px=cell_px, char_aspect=char_aspect)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), float(fps), canvas.size)
    if not writer.isOpened():
        raise ValueError("无法写出字符视频")
    count = 0
    base_size = first.size
    try:
        writer.write(cv2.cvtColor(np.asarray(canvas.convert("L")), cv2.COLOR_GRAY2BGR))
        count = 1
        for gray in pending:
            if gray.size != base_size:
                gray = gray.resize(base_size, _RESAMPLE)
            frame = resize_gray(gray if gray.mode == "L" else gray.convert("L"), columns, char_aspect)
            art = pixels_to_ascii(frame, ramp, invert, stretch=False)
            painted = paint_frame(art, invert=invert, cell_px=cell_px, char_aspect=char_aspect)
            writer.write(cv2.cvtColor(np.asarray(painted.convert("L")), cv2.COLOR_GRAY2BGR))
            count += 1
    finally:
        writer.release()
    if count < 1 or not path.exists() or path.stat().st_size == 0:
        raise ValueError("无法写出字符视频")
    return opening, fitted.width, fitted.height, count


def _finish(silent: Path, source: Path, dest: Path) -> bool:
    ffmpeg = _ffmpeg_exe()
    if ffmpeg is None:
        return False
    if _source_has_audio(ffmpeg, source) and _transcode(ffmpeg, silent, source, dest, audio=True):
        return True
    _transcode(ffmpeg, silent, source, dest, audio=False)
    return False


def _ffmpeg_exe() -> str | None:
    cached = getattr(_ffmpeg_exe, "path", None)
    if cached:
        return cached
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    try:
        path = imageio_ffmpeg.get_ffmpeg_exe()
    except OSError:
        return None
    _ffmpeg_exe.path = path
    return path


def _source_has_audio(ffmpeg: str, source: Path) -> bool:
    completed = _run([ffmpeg, "-hide_banner", "-i", str(source)])
    text = completed.stderr.decode("utf-8", errors="replace")
    return "Audio:" in text


def _transcode(ffmpeg: str, silent: Path, source: Path, dest: Path, *, audio: bool) -> bool:
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent)]
    if audio:
        command += ["-i", str(source), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-shortest"]
    else:
        command += ["-an"]
    command += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest)]
    completed = _run(command)
    return completed.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    return subprocess.run(command, capture_output=True, creationflags=flags)

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from ptasc.tools.full_video import _ffmpeg_exe, render_full_file


def _silent_clip(path: Path, colors: tuple[int, ...], fps: float = 10) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (32, 32))
    for color in colors:
        frame = cv2.cvtColor(np.full((32, 32), color, dtype="uint8"), cv2.COLOR_GRAY2BGR)
        writer.write(frame)
    writer.release()


def test_full_render_keeps_frames_past_the_preview_cap(tmp_path: Path):
    source = tmp_path / "source.mp4"
    _silent_clip(source, (0, 255, 0, 255, 0, 255))
    full = render_full_file(
        source,
        columns=4,
        char_aspect=2.0,
        ramp=" @",
        invert=False,
        sample_fps=5,
        max_edge=32,
        cell_px=8,
    )

    assert full.frame_count == 3
    assert full.fps == pytest.approx(5)
    assert full.opening.startswith("@@@@")
    assert full.mp4.startswith(b"\x00\x00\x00") or b"ftyp" in full.mp4[:32]


def test_full_render_keeps_source_audio(tmp_path: Path):
    ffmpeg = _ffmpeg_exe()
    if ffmpeg is None:
        pytest.skip("ffmpeg is not available")
    source = tmp_path / "tone.mp4"
    created = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:r=10:d=1",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        capture_output=True,
    )
    if created.returncode != 0 or not source.exists():
        pytest.skip("ffmpeg cannot build a clip with audio")
    full = render_full_file(
        source,
        columns=8,
        char_aspect=2.0,
        ramp=" @",
        invert=False,
        sample_fps=8,
        max_edge=64,
        cell_px=8,
    )
    assert full.has_audio
    assert full.frame_count >= 8
    probed = subprocess.run([ffmpeg, "-hide_banner", "-i", str(_write(tmp_path, full.mp4))], capture_output=True)
    text = probed.stderr.decode("utf-8", errors="replace")
    assert "Audio:" in text


def _write(folder: Path, data: bytes) -> Path:
    path = folder / "ascii.mp4"
    path.write_bytes(data)
    return path

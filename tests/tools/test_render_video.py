import tempfile
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from ptasc.render_video import render_still_frames, render_video
from ptasc.tools.video_frames import read_frames


def _gif(colors: list[int]) -> bytes:
    frames = [Image.new("L", (16, 16), color) for color in colors]
    buffer = BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )
    return buffer.getvalue()


def test_black_and_white_frames_keep_their_shade_and_replay():
    preview = render_video(
        video=_gif([0, 255]),
        suffix=".gif",
        columns=4,
        char_aspect=2.0,
        ramp=" @",
        invert=False,
        sample_fps=8,
        max_frames=10,
        max_seconds=5,
        cell_px=8,
    )

    assert preview.frames == ("@@@@\n@@@@\n", "    \n    \n")
    assert preview.rows == 2
    assert preview.fps == pytest.approx(10)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "ascii.mp4"
        path.write_bytes(preview.mp4)
        capture = cv2.VideoCapture(str(path))
        try:
            assert capture.isOpened()
            count = 0
            while True:
                ok, _frame = capture.read()
                if not ok:
                    break
                count += 1
            assert count == 2
        finally:
            capture.release()


def test_frame_cap_stops_early():
    frames, _fps = read_frames(_gif([0, 255, 128]), ".gif", sample_fps=10, max_frames=1, max_seconds=5, max_edge=64)

    assert len(frames) == 1


def test_sampled_frames_skip_the_original_file():
    black = BytesIO()
    white = BytesIO()
    Image.new("L", (16, 16), 0).save(black, format="PNG")
    Image.new("L", (16, 16), 255).save(white, format="PNG")
    preview = render_still_frames(
        frames=[black.getvalue(), white.getvalue()],
        fps=8,
        columns=4,
        char_aspect=2.0,
        ramp=" @",
        invert=False,
        cell_px=8,
        max_edge=64,
        encode=False,
    )

    assert preview.frames == ("@@@@\n@@@@\n", "    \n    \n")
    assert preview.mp4 == b""


def test_mp4_grab_skips_frames_and_stops_early():
    writer_path = Path(tempfile.mkdtemp()) / "source.mp4"
    writer = cv2.VideoWriter(str(writer_path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (32, 32))
    for color in (0, 255, 0, 255, 0, 255):
        frame = cv2.cvtColor(np.full((32, 32), color, dtype="uint8"), cv2.COLOR_GRAY2BGR)
        writer.write(frame)
    writer.release()
    frames, fps = read_frames(
        writer_path.read_bytes(),
        ".mp4",
        sample_fps=5,
        max_frames=2,
        max_seconds=5,
        max_edge=32,
    )
    writer_path.unlink()

    assert len(frames) == 2
    assert fps == pytest.approx(5)


def test_reject_bytes_that_are_not_a_video():
    with pytest.raises(ValueError):
        read_frames(b"not-a-video", ".gif", sample_fps=8, max_frames=4, max_seconds=2, max_edge=64)

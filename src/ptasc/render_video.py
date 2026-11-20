"""把视频字节渲染成字符帧和字符视频。不写磁盘，也不记日志。"""

from dataclasses import dataclass

from PIL import Image

_RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

from ptasc.tools.ascii_canvas import encode_mp4, paint_frame
from ptasc.tools.pixels_to_ascii import pixels_to_ascii
from ptasc.tools.resize_gray import resize_gray
from ptasc.tools.video_frames import load_still_frames, read_frames

FRAME_BREAK = "\n\f\n"


@dataclass(frozen=True)
class VideoPreview:
    frames: tuple[str, ...]
    columns: int
    rows: int
    fps: float
    mp4: bytes

    @property
    def ascii_art(self) -> str:
        parts = [frame[:-1] if frame.endswith("\n") else frame for frame in self.frames]
        return FRAME_BREAK.join(parts) + "\n"


def render_video(
    *,
    video: bytes,
    suffix: str,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    sample_fps: float,
    max_frames: int,
    max_seconds: float,
    cell_px: int,
    max_edge: int = 480,
    encode: bool = True,
) -> VideoPreview:
    sampled, fps = read_frames(
        video,
        suffix,
        sample_fps=sample_fps,
        max_frames=max_frames,
        max_seconds=max_seconds,
        max_edge=max_edge,
    )
    return _compose(
        sampled,
        fps=fps,
        columns=columns,
        char_aspect=char_aspect,
        ramp=ramp,
        invert=invert,
        cell_px=cell_px,
        encode=encode,
    )


def render_prepared(
    frames: list[Image.Image],
    *,
    fps: float,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    cell_px: int,
    encode: bool = True,
) -> VideoPreview:
    if not frames:
        raise ValueError("视频没有画面")
    return _compose(
        frames,
        fps=fps,
        columns=columns,
        char_aspect=char_aspect,
        ramp=ramp,
        invert=invert,
        cell_px=cell_px,
        encode=encode,
    )


def render_still_frames(
    *,
    frames: list[bytes],
    fps: float,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    cell_px: int,
    max_edge: int = 480,
    encode: bool = True,
) -> VideoPreview:
    return _compose(
        load_still_frames(frames, max_edge),
        fps=fps,
        columns=columns,
        char_aspect=char_aspect,
        ramp=ramp,
        invert=invert,
        cell_px=cell_px,
        encode=encode,
    )


def _compose(
    sampled: list[Image.Image],
    *,
    fps: float,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    cell_px: int,
    encode: bool,
) -> VideoPreview:
    fitted = [_fit(frame, sampled[0].size, columns, char_aspect) for frame in sampled]
    arts = tuple(pixels_to_ascii(frame, ramp, invert, stretch=False) for frame in fitted)
    mp4 = b""
    if encode:
        canvases = [paint_frame(art, invert=invert, cell_px=cell_px, char_aspect=char_aspect) for art in arts]
        mp4 = encode_mp4(canvases, fps)
    return VideoPreview(
        frames=arts,
        columns=fitted[0].width,
        rows=fitted[0].height,
        fps=fps,
        mp4=mp4,
    )


def _fit(frame: Image.Image, size: tuple[int, int], columns: int, char_aspect: float) -> Image.Image:
    gray = frame if frame.mode == "L" else frame.convert("L")
    if gray.size != size:
        gray = gray.resize(size, _RESAMPLE)
    return resize_gray(gray, columns, char_aspect)

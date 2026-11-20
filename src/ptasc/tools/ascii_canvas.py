"""把字符帧画成画面，并编成 mp4。"""

import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 页面预览用等宽字体。MP4 也必须用等宽格子，否则 . 和 @ 宽窄不同，画面会被拉变形。
_MONO_FILES = (
    "consola.ttf",
    "CascadiaMono.ttf",
    "cour.ttf",
    "DejaVuSansMono.ttf",
    "LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/Library/Fonts/Courier New.ttf",
)
_fonts: dict[int, ImageFont.ImageFont] = {}


def paint_frame(art: str, *, invert: bool, cell_px: int, char_aspect: float = 2.0) -> Image.Image:
    lines = art.splitlines() or [""]
    font = _mono_font(cell_px)
    cell_width, cell_height = _cell_size(font, char_aspect)
    columns = max(len(line) for line in lines)
    width = max(cell_width * columns, 2)
    height = max(cell_height * len(lines), 2)
    background = 0 if invert else 255
    ink = 255 if invert else 0
    canvas = Image.new("L", (_even(width), _even(height)), background)
    draw = ImageDraw.Draw(canvas)
    advance = int(round(font.getlength("M")))
    for index, line in enumerate(lines):
        y = index * cell_height
        if _uniform(font) and cell_width == advance:
            draw.text((0, y), line, fill=ink, font=font)
            continue
        for column, char in enumerate(line):
            draw.text((column * cell_width, y), char, fill=ink, font=font)
    return canvas


def _mono_font(size: int) -> ImageFont.ImageFont:
    cached = _fonts.get(size)
    if cached is not None:
        return cached
    for name in _MONO_FILES:
        try:
            font = ImageFont.truetype(name, size=size)
        except OSError:
            continue
        _fonts[size] = font
        return font
    font = ImageFont.load_default(size=size)
    _fonts[size] = font
    return font


def _cell_size(font: ImageFont.ImageFont, char_aspect: float) -> tuple[int, int]:
    ascent, descent = font.getmetrics()
    glyph_height = max(1, ascent + descent)
    advance = max(1, int(round(font.getlength("M"))))
    if not _uniform(font):
        advance = max(advance, *(int(round(font.getlength(char))) for char in " .@#%W"))
    aspect = char_aspect if char_aspect > 0 else 2.0
    cell_width = max(advance, int(round(glyph_height / aspect)))
    cell_height = max(glyph_height, int(round(cell_width * aspect)))
    return cell_width, cell_height


def _uniform(font: ImageFont.ImageFont) -> bool:
    widths = {round(font.getlength(char)) for char in " .M@#%"}
    return len(widths) == 1


def encode_mp4(frames: list[Image.Image], fps: float) -> bytes:
    import cv2

    if not frames:
        raise ValueError("视频没有画面")
    width, height = frames[0].size
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "ascii.mp4"
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            float(fps),
            (width, height),
        )
        if not writer.isOpened():
            raise ValueError("无法写出字符视频")
        try:
            for frame in frames:
                gray = np.asarray(frame.convert("L"))
                writer.write(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
        finally:
            writer.release()
        data = path.read_bytes()
    if not data:
        raise ValueError("无法写出字符视频")
    return data


def _even(value: int) -> int:
    return value if value % 2 == 0 else value + 1

"""把图片字节渲染成字符画。不写磁盘，也不记日志。"""

from dataclasses import dataclass

from ptasc.tools.image_gray import grayscale_from_bytes
from ptasc.tools.pixels_to_ascii import pixels_to_ascii
from ptasc.tools.resize_gray import resize_gray


@dataclass(frozen=True)
class Preview:
    ascii_art: str
    columns: int
    rows: int


def render_image(
    *,
    image: bytes,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
) -> Preview:
    fitted = resize_gray(grayscale_from_bytes(image), columns, char_aspect)
    return Preview(
        ascii_art=pixels_to_ascii(fitted, ramp, invert),
        columns=fitted.width,
        rows=fitted.height,
    )

"""按字符格子的高宽比，把灰度图缩成字符行列。"""

from PIL import Image

_RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


def character_rows(width: int, height: int, columns: int, char_aspect: float) -> int:
    if width < 1 or height < 1:
        raise ValueError("图片宽高必须为正")
    if columns < 1:
        raise ValueError("列数必须为正")
    if char_aspect <= 0:
        raise ValueError("字符高宽比必须为正")
    return max(1, round(columns * height / width / char_aspect))


def resize_gray(image: Image.Image, columns: int, char_aspect: float) -> Image.Image:
    gray = image if image.mode == "L" else image.convert("L")
    rows = character_rows(gray.width, gray.height, columns, char_aspect)
    return gray.resize((columns, rows), _RESAMPLE)

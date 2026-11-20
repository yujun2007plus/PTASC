"""把图片读成亮度灰度图。"""

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def grayscale_from_bytes(data: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(data)) as image:
            gray = image.convert("L")
            gray.load()
            return gray.copy()
    except UnidentifiedImageError as exc:
        raise ValueError("无法识别图片") from exc


def load_grayscale(path: Path) -> Image.Image:
    return grayscale_from_bytes(path.read_bytes())

"""校验浏览器提交的转换参数。"""

from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path

from ptasc.config.settings import AsciiSettings

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_COLUMNS = 240
MAX_RAMP_LENGTH = 120


@dataclass(frozen=True)
class ConvertRequest:
    image: bytes
    filename: str
    columns: int
    char_aspect: float
    ramp: str
    invert: bool


def parse_convert_payload(payload: object, defaults: AsciiSettings) -> ConvertRequest:
    if not isinstance(payload, dict):
        raise ValueError("请求必须是 JSON 对象")
    encoded = payload.get("image_base64", "")
    if not isinstance(encoded, str) or encoded.strip() == "":
        raise ValueError("缺少图片数据")
    if "," in encoded and encoded.lstrip().lower().startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        image = b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError("图片数据不是有效的 base64") from exc
    if not image:
        raise ValueError("图片是空的")
    if len(image) > MAX_IMAGE_BYTES:
        raise ValueError("图片超过 8MB")

    filename = payload.get("filename", "image.png")
    if not isinstance(filename, str) or filename.strip() == "":
        filename = "image.png"
    filename = Path(filename).name

    columns = payload.get("columns", defaults.columns)
    if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= MAX_COLUMNS:
        raise ValueError(f"列数必须是 1 到 {MAX_COLUMNS} 的整数")

    ramp = payload.get("ramp", defaults.ramp)
    if not isinstance(ramp, str) or ramp == "" or len(ramp) > MAX_RAMP_LENGTH:
        raise ValueError("字符坡道必须是非空字符串")

    invert = payload.get("invert", defaults.invert)
    if not isinstance(invert, bool):
        raise ValueError("invert 必须是 true 或 false")

    return ConvertRequest(
        image=image,
        filename=filename,
        columns=columns,
        char_aspect=defaults.char_aspect,
        ramp=ramp,
        invert=invert,
    )

"""校验浏览器提交的转换参数。"""

from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from ptasc.config.settings import AsciiSettings
from ptasc.tools.video_frames import is_video_name

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 32 * 1024 * 1024
MAX_FULL_VIDEO_BYTES = 512 * 1024 * 1024
MAX_FRAME_BYTES = 1024 * 1024
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


@dataclass(frozen=True)
class VideoRequest:
    video: bytes
    frames: tuple[bytes, ...]
    filename: str
    suffix: str
    columns: int
    char_aspect: float
    ramp: str
    invert: bool
    fps: float
    preview_id: str
    render_id: str


def _decode_base64(encoded: object, *, empty: str, invalid: str) -> bytes:
    if not isinstance(encoded, str) or encoded.strip() == "":
        raise ValueError(empty)
    if "," in encoded and encoded.lstrip().lower().startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        data = b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError(invalid) from exc
    if not data:
        raise ValueError(empty)
    return data


def parse_video_payload(payload: object, defaults: AsciiSettings) -> VideoRequest:
    if not isinstance(payload, dict):
        raise ValueError("请求必须是 JSON 对象")
    preview_id = _token(payload.get("preview_id", ""), "预览编号无效")
    render_id = _token(payload.get("render_id", ""), "转换编号无效")
    raw_frames = payload.get("frames_base64")
    frames: tuple[bytes, ...] = ()
    video = b""
    video_field = payload.get("video_base64", "")
    if isinstance(raw_frames, list) and raw_frames:
        if len(raw_frames) > defaults.video_max_frames:
            raise ValueError(f"画面不能超过 {defaults.video_max_frames} 帧")
        decoded: list[bytes] = []
        for item in raw_frames:
            frame = _decode_base64(item, empty="视频画面是空的", invalid="视频画面不是有效的 base64")
            if len(frame) > MAX_FRAME_BYTES:
                raise ValueError("单帧画面超过 1MB")
            decoded.append(frame)
        frames = tuple(decoded)
    elif isinstance(video_field, str) and video_field.strip():
        video = _decode_base64(video_field, empty="缺少视频数据", invalid="视频数据不是有效的 base64")
        if len(video) > MAX_VIDEO_BYTES:
            raise ValueError("视频超过 32MB，请换用页面里的抽帧")
    elif not preview_id and not render_id:
        raise ValueError("缺少视频数据")

    filename = payload.get("filename", "clip.mp4")
    if not isinstance(filename, str) or filename.strip() == "":
        filename = "clip.mp4"
    if not is_video_name(filename):
        raise ValueError("请提供 mp4、webm、mov、mkv、avi 或 gif")
    filename = Path(filename).name
    fps = payload.get("fps", defaults.video_fps)
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not 1 <= float(fps) <= 30:
        raise ValueError("帧率必须在 1 到 30 之间")

    columns = payload.get("columns", defaults.columns)
    if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= MAX_COLUMNS:
        raise ValueError(f"列数必须是 1 到 {MAX_COLUMNS} 的整数")

    ramp = payload.get("ramp", defaults.ramp)
    if not isinstance(ramp, str) or ramp == "" or len(ramp) > MAX_RAMP_LENGTH:
        raise ValueError("字符坡道必须是非空字符串")

    invert = payload.get("invert", defaults.invert)
    if not isinstance(invert, bool):
        raise ValueError("invert 必须是 true 或 false")

    return VideoRequest(
        video=video,
        frames=frames,
        filename=filename,
        suffix=Path(filename).suffix.lower(),
        columns=columns,
        char_aspect=defaults.char_aspect,
        ramp=ramp,
        invert=invert,
        fps=float(fps),
        preview_id=preview_id,
        render_id=render_id,
    )


def _token(value: object, message: str) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(message)
    token = value.strip()
    if token and (len(token) != 16 or any(char not in "0123456789abcdef" for char in token)):
        raise ValueError(message)
    return token


def parse_full_headers(headers: object, defaults: AsciiSettings) -> tuple[str, int, str, bool]:
    read = getattr(headers, "get", None)
    if read is None:
        raise ValueError("请求头无效")
    filename = unquote(str(read("X-Ptasc-Filename", "") or "")).strip()
    if not filename or not is_video_name(filename):
        raise ValueError("请提供 mp4、webm、mov、mkv、avi 或 gif")
    filename = Path(filename).name
    raw_columns = read("X-Ptasc-Columns", "")
    if raw_columns in (None, ""):
        columns = defaults.columns
    else:
        try:
            columns = int(str(raw_columns))
        except ValueError as exc:
            raise ValueError(f"列数必须是 1 到 {MAX_COLUMNS} 的整数") from exc
    if isinstance(columns, bool) or not 1 <= columns <= MAX_COLUMNS:
        raise ValueError(f"列数必须是 1 到 {MAX_COLUMNS} 的整数")
    raw_ramp = read("X-Ptasc-Ramp", "")
    ramp = unquote(str(raw_ramp)) if raw_ramp not in (None, "") else defaults.ramp
    if not isinstance(ramp, str) or ramp == "" or len(ramp) > MAX_RAMP_LENGTH:
        raise ValueError("字符坡道必须是非空字符串")
    raw_invert = str(read("X-Ptasc-Invert", "false") or "false").strip().lower()
    if raw_invert not in {"true", "false", "1", "0"}:
        raise ValueError("invert 必须是 true 或 false")
    return filename, columns, ramp, raw_invert in {"true", "1"}

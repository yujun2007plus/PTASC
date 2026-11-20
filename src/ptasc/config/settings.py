"""把 YAML 标量转成字符画设置。"""

from dataclasses import dataclass
from pathlib import Path

from ptasc.config.parse import load_yaml_subset


@dataclass(frozen=True)
class AsciiSettings:
    columns: int
    char_aspect: float
    ramp: str
    invert: bool
    video_fps: float = 8
    video_max_frames: int = 120
    video_max_seconds: float = 15
    video_max_edge: int = 480
    video_cell_px: int = 10


def _require_positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} 必须是正整数")
    return value


def _require_positive_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} 必须是正数")
    return float(value)


def _bounded_int(data: dict[str, object], key: str, default: int, low: int, high: int) -> int:
    number = _require_positive_int(data.get(key, default), key)
    if not low <= number <= high:
        raise ValueError(f"{key} 必须在 {low} 到 {high} 之间")
    return number


def _bounded_float(data: dict[str, object], key: str, default: float, low: float, high: float) -> float:
    number = _require_positive_float(data.get(key, default), key)
    if not low <= number <= high:
        raise ValueError(f"{key} 必须在 {low} 到 {high} 之间")
    return number


def settings_from_mapping(data: dict[str, object]) -> AsciiSettings:
    required = ("columns", "char_aspect", "ramp", "invert")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError("配置缺少字段: " + ", ".join(missing))
    ramp = data["ramp"]
    invert = data["invert"]
    if not isinstance(ramp, str) or ramp == "":
        raise ValueError("ramp 必须是非空字符串")
    if not isinstance(invert, bool):
        raise ValueError("invert 必须是 true 或 false")
    return AsciiSettings(
        columns=_require_positive_int(data["columns"], "columns"),
        char_aspect=_require_positive_float(data["char_aspect"], "char_aspect"),
        ramp=ramp,
        invert=invert,
        video_fps=_bounded_float(data, "video_fps", 8, 1, 30),
        video_max_frames=_bounded_int(data, "video_max_frames", 120, 1, 600),
        video_max_seconds=_bounded_float(data, "video_max_seconds", 15, 0.2, 120),
        video_max_edge=_bounded_int(data, "video_max_edge", 480, 64, 960),
        video_cell_px=_bounded_int(data, "video_cell_px", 10, 6, 24),
    )


def load_settings(path: Path) -> AsciiSettings:
    return settings_from_mapping(load_yaml_subset(path))

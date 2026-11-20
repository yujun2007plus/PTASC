"""组装并写入一次转换的 meta.json。"""

import json
from datetime import datetime, timezone
from pathlib import Path


def make_task_id(source_sha256: str, now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    stamp = moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{source_sha256[:8]}"


def build_meta(
    *,
    task_id: str,
    source_name: str,
    source_sha256: str,
    columns: int,
    rows: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    tool_version: str,
    created_at: str,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "source_name": source_name,
        "source_sha256": source_sha256,
        "columns": columns,
        "rows": rows,
        "char_aspect": char_aspect,
        "ramp": ramp,
        "invert": invert,
        "output": "ascii.txt",
        "tool_version": tool_version,
        "created_at": created_at,
    }


def write_meta(path: Path, meta: dict[str, object]) -> None:
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

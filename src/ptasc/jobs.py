"""把一次预览落成任务目录，并记下审计日志。"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ptasc import __version__
from ptasc.audit.meta import build_meta, make_task_id
from ptasc.audit.task_store import claim_task_dir, write_task_files
from ptasc.render import render_image
from ptasc.tools.checksum import content_sha256


@dataclass(frozen=True)
class Conversion:
    task_id: str
    ascii_art: str
    columns: int
    rows: int
    source_sha256: str


def convert_bytes(
    *,
    root: Path,
    image: bytes,
    source_name: str,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    runtime_log: logging.Logger,
    audit_log: logging.Logger,
) -> Conversion:
    preview = render_image(
        image=image,
        columns=columns,
        char_aspect=char_aspect,
        ramp=ramp,
        invert=invert,
    )
    digest = content_sha256(image)
    created = datetime.now(timezone.utc)
    task_dir = claim_task_dir(root / "data" / "tasks", make_task_id(digest, created))
    write_task_files(
        task_dir,
        ascii_art=preview.ascii_art,
        meta=build_meta(
            task_id=task_dir.name,
            source_name=source_name,
            source_sha256=digest,
            columns=preview.columns,
            rows=preview.rows,
            char_aspect=char_aspect,
            ramp=ramp,
            invert=invert,
            tool_version=__version__,
            created_at=created.isoformat(),
        ),
    )
    audit_log.info(
        "task_id=%s sha256=%s columns=%s rows=%s output=ascii.txt",
        task_dir.name,
        digest,
        preview.columns,
        preview.rows,
    )
    runtime_log.info("字符画已写入 %s", task_dir / "ascii.txt")
    return Conversion(
        task_id=task_dir.name,
        ascii_art=preview.ascii_art,
        columns=preview.columns,
        rows=preview.rows,
        source_sha256=digest,
    )

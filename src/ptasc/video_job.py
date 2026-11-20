"""把一次字符视频落成任务目录，并记下审计日志。"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from ptasc import __version__
from ptasc.audit.meta import build_meta, make_task_id
from ptasc.audit.task_store import claim_task_dir, write_task_files
from ptasc.render_video import VideoPreview, render_prepared, render_still_frames, render_video
from ptasc.tools.checksum import content_sha256
from ptasc.tools.full_video import FullVideo, render_full_file


@dataclass(frozen=True)
class VideoConversion:
    task_id: str
    preview: VideoPreview
    source_sha256: str


def convert_video_bytes(
    *,
    root: Path,
    video: bytes,
    source_name: str,
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
    frames: tuple[bytes, ...] = (),
    playback_fps: float = 0,
    prepared: tuple[Image.Image, ...] = (),
    source_sha256: str = "",
    runtime_log: logging.Logger,
    audit_log: logging.Logger,
) -> VideoConversion:
    if prepared:
        if not source_sha256:
            raise ValueError("缺少视频校验")
        preview = render_prepared(
            list(prepared),
            fps=playback_fps or sample_fps,
            columns=columns,
            char_aspect=char_aspect,
            ramp=ramp,
            invert=invert,
            cell_px=cell_px,
            encode=True,
        )
        digest = source_sha256
    elif frames:
        preview = render_still_frames(
            frames=list(frames),
            fps=playback_fps or sample_fps,
            columns=columns,
            char_aspect=char_aspect,
            ramp=ramp,
            invert=invert,
            cell_px=cell_px,
            max_edge=max_edge,
        )
        digest = content_sha256(b"".join(frames))
    else:
        preview = render_video(
            video=video,
            suffix=suffix,
            columns=columns,
            char_aspect=char_aspect,
            ramp=ramp,
            invert=invert,
            sample_fps=sample_fps,
            max_frames=max_frames,
            max_seconds=max_seconds,
            cell_px=cell_px,
            max_edge=max_edge,
        )
        digest = content_sha256(video)
    created = datetime.now(timezone.utc)
    task_dir = claim_task_dir(root / "data" / "tasks", make_task_id(digest, created))
    write_task_files(
        task_dir,
        ascii_art=preview.ascii_art,
        video=preview.mp4,
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
            output="ascii.mp4",
            extra={
                "kind": "video",
                "frame_count": len(preview.frames),
                "fps": preview.fps,
            },
        ),
    )
    audit_log.info(
        "task_id=%s sha256=%s columns=%s rows=%s frames=%s fps=%s output=ascii.mp4",
        task_dir.name,
        digest,
        preview.columns,
        preview.rows,
        len(preview.frames),
        preview.fps,
    )
    runtime_log.info("字符视频已写入 %s", task_dir / "ascii.mp4")
    return VideoConversion(task_id=task_dir.name, preview=preview, source_sha256=digest)


def convert_full_path(
    *,
    root: Path,
    source_path: Path,
    columns: int,
    char_aspect: float,
    ramp: str,
    invert: bool,
    sample_fps: float,
    max_edge: int,
    cell_px: int,
    runtime_log: logging.Logger,
    audit_log: logging.Logger,
) -> tuple[VideoConversion, FullVideo]:
    full = render_full_file(
        source_path,
        columns=columns,
        char_aspect=char_aspect,
        ramp=ramp,
        invert=invert,
        sample_fps=sample_fps,
        max_edge=max_edge,
        cell_px=cell_px,
    )
    saved = save_full_video(
        root=root,
        source_name=source_path.name,
        full=full,
        char_aspect=char_aspect,
        ramp=ramp,
        invert=invert,
        runtime_log=runtime_log,
        audit_log=audit_log,
    )
    return saved, full


def save_full_video(
    *,
    root: Path,
    source_name: str,
    full: FullVideo,
    char_aspect: float,
    ramp: str,
    invert: bool,
    runtime_log: logging.Logger,
    audit_log: logging.Logger,
) -> VideoConversion:
    created = datetime.now(timezone.utc)
    task_dir = claim_task_dir(root / "data" / "tasks", make_task_id(full.source_sha256, created))
    preview = VideoPreview(
        frames=(full.opening,),
        columns=full.columns,
        rows=full.rows,
        fps=full.fps,
        mp4=full.mp4,
    )
    write_task_files(
        task_dir,
        ascii_art=full.opening,
        video=full.mp4,
        meta=build_meta(
            task_id=task_dir.name,
            source_name=source_name,
            source_sha256=full.source_sha256,
            columns=full.columns,
            rows=full.rows,
            char_aspect=char_aspect,
            ramp=ramp,
            invert=invert,
            tool_version=__version__,
            created_at=created.isoformat(),
            output="ascii.mp4",
            extra={
                "kind": "video",
                "frame_count": full.frame_count,
                "fps": full.fps,
                "audio": full.has_audio,
                "full": True,
            },
        ),
    )
    audit_log.info(
        "task_id=%s sha256=%s columns=%s rows=%s frames=%s fps=%s audio=%s output=ascii.mp4",
        task_dir.name,
        full.source_sha256,
        full.columns,
        full.rows,
        full.frame_count,
        full.fps,
        full.has_audio,
    )
    runtime_log.info("完整字符视频已写入 %s", task_dir / "ascii.mp4")
    return VideoConversion(task_id=task_dir.name, preview=preview, source_sha256=full.source_sha256)

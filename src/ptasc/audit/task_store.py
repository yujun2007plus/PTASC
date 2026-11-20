"""在任务根目录里占一个目录，并写入这次转换的两个文件。"""

from pathlib import Path

from ptasc.audit.meta import write_meta


def claim_task_dir(tasks_root: Path, task_id: str) -> Path:
    tasks_root.mkdir(parents=True, exist_ok=True)
    candidate = tasks_root / task_id
    suffix = 1
    while candidate.exists():
        suffix += 1
        candidate = tasks_root / f"{task_id}-{suffix}"
    candidate.mkdir()
    return candidate


def write_task_files(task_dir: Path, *, ascii_art: str, meta: dict[str, object]) -> None:
    (task_dir / "ascii.txt").write_text(ascii_art, encoding="utf-8")
    write_meta(task_dir / "meta.json", meta)

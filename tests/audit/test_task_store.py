import json

from ptasc.audit.task_store import claim_task_dir, write_task_files


def test_second_claim_adds_a_suffix(tmp_path):
    first = claim_task_dir(tmp_path, "same-id")
    second = claim_task_dir(tmp_path, "same-id")

    assert first.name == "same-id"
    assert second.name == "same-id-2"


def test_write_task_files_keeps_art_and_meta_together(tmp_path):
    task_dir = claim_task_dir(tmp_path, "task")
    write_task_files(task_dir, ascii_art="A\n", meta={"task_id": task_dir.name, "rows": 1})

    assert (task_dir / "ascii.txt").read_text(encoding="utf-8") == "A\n"
    assert json.loads((task_dir / "meta.json").read_text(encoding="utf-8"))["task_id"] == "task"

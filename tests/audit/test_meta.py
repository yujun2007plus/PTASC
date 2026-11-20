import json
from datetime import datetime, timezone

from ptasc.audit.meta import build_meta, make_task_id, write_meta


def test_task_id_uses_time_and_hash_prefix():
    moment = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)

    assert make_task_id("abcdef1234567890", moment) == "20261120T120000000000Z-abcdef12"


def test_write_meta_roundtrip(tmp_path):
    meta = build_meta(
        task_id="task",
        source_name="photo.jpg",
        source_sha256="abc",
        columns=16,
        rows=8,
        char_aspect=2.0,
        ramp=" @",
        invert=False,
        tool_version="0.1.0",
        created_at="2026-11-20T12:00:00+00:00",
    )
    path = tmp_path / "meta.json"
    write_meta(path, meta)

    assert json.loads(path.read_text(encoding="utf-8"))["rows"] == 8

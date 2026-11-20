import json
import threading
import urllib.request
from base64 import b64encode
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from ptasc.api.request import parse_convert_payload
from ptasc.api.server import make_server
from ptasc.api.static_files import resolve_web_file
from ptasc.config.settings import AsciiSettings


def test_web_file_cannot_escape(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("ok", encoding="utf-8")

    assert resolve_web_file(web, "/index.html").name == "index.html"
    assert resolve_web_file(web, "/../secrets.txt") is None


def test_payload_rejects_wide_output():
    settings = AsciiSettings(columns=80, char_aspect=2.0, ramp=" @", invert=False)
    with pytest.raises(ValueError):
        parse_convert_payload(
            {"image_base64": b64encode(b"png").decode("ascii"), "columns": 9999},
            settings,
        )


def _request(port: int, path: str, body: bytes) -> dict[str, object]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def test_convert_previews_until_save(tmp_path: Path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("图片转字符画", encoding="utf-8")
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "runtime.yaml").write_text(
        'columns: 80\nchar_aspect: 2.0\nramp: " .:-=+*#%@"\ninvert: false\n',
        encoding="utf-8",
    )
    server = make_server(tmp_path, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        buffer = BytesIO()
        Image.new("L", (12, 12), color=255).save(buffer, format="PNG")
        body = json.dumps(
            {
                "filename": "blank.png",
                "image_base64": b64encode(buffer.getvalue()).decode("ascii"),
                "columns": 24,
                "ramp": " @",
                "invert": False,
            }
        ).encode("utf-8")
        preview = _request(port, "/api/convert", body)
        assert preview["columns"] == 24
        assert "task_id" not in preview
        assert not (tmp_path / "data" / "tasks").exists()

        saved = _request(port, "/api/save", body)
        tasks = list((tmp_path / "data" / "tasks").iterdir())
        assert len(tasks) == 1
        assert (tasks[0] / "ascii.txt").read_text(encoding="utf-8") == saved["ascii"]
        assert saved["task_id"] == tasks[0].name
    finally:
        server.shutdown()
        server.server_close()

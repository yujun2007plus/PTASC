import json
import threading
import urllib.error
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


def test_video_previews_until_save(tmp_path: Path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("ok", encoding="utf-8")
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "runtime.yaml").write_text(
        'columns: 80\nchar_aspect: 2.0\nramp: " @"\ninvert: false\n',
        encoding="utf-8",
    )
    server = make_server(tmp_path, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        frames = [Image.new("L", (16, 16), color) for color in (0, 255)]
        buffer = BytesIO()
        frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
        body = json.dumps(
            {
                "filename": "clip.gif",
                "video_base64": b64encode(buffer.getvalue()).decode("ascii"),
                "columns": 4,
                "ramp": " @",
                "invert": False,
            }
        ).encode("utf-8")
        preview = _request(port, "/api/convert-video", body)
        assert preview["frame_count"] == 2
        assert "task_id" not in preview
        assert not (tmp_path / "data" / "tasks").exists()

        saved = _request(port, "/api/save-video", body)
        tasks = list((tmp_path / "data" / "tasks").iterdir())
        assert len(tasks) == 1
        assert saved["task_id"] == tasks[0].name
        assert (tasks[0] / "ascii.mp4").stat().st_size > 0
        assert "\f" in (tasks[0] / "ascii.txt").read_text(encoding="utf-8")

        reused = _request(
            port,
            "/api/convert-video",
            json.dumps(
                {
                    "filename": "clip.gif",
                    "preview_id": preview["preview_id"],
                    "columns": 8,
                    "ramp": " @",
                    "invert": False,
                }
            ).encode("utf-8"),
        )
        assert reused["preview_id"] == preview["preview_id"]
        assert reused["columns"] == 8
        assert reused["frame_count"] == 2
        saved_again = _request(
            port,
            "/api/save-video",
            json.dumps(
                {
                    "filename": "clip.gif",
                    "preview_id": preview["preview_id"],
                    "columns": 8,
                    "ramp": " @",
                    "invert": False,
                }
            ).encode("utf-8"),
        )
        assert saved_again["columns"] == 8
        assert len(list((tmp_path / "data" / "tasks").iterdir())) == 2
    finally:
        server.shutdown()
        server.server_close()


def test_video_preview_id_expires(tmp_path: Path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("ok", encoding="utf-8")
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "runtime.yaml").write_text(
        'columns: 80\nchar_aspect: 2.0\nramp: " @"\ninvert: false\n',
        encoding="utf-8",
    )
    server = make_server(tmp_path, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        body = json.dumps(
            {
                "filename": "clip.gif",
                "preview_id": "0" * 16,
                "columns": 4,
                "ramp": " @",
                "invert": False,
            }
        ).encode("utf-8")
        with pytest.raises(urllib.error.HTTPError) as caught:
            _request(port, "/api/convert-video", body)
        assert caught.value.code == 400
        assert "过期" in json.load(caught.value)["error"]
    finally:
        server.shutdown()
        server.server_close()


def test_full_video_download_is_mp4(tmp_path: Path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("ok", encoding="utf-8")
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "runtime.yaml").write_text(
        'columns: 80\nchar_aspect: 2.0\nramp: " @"\ninvert: false\n',
        encoding="utf-8",
    )
    server = make_server(tmp_path, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        frames = [Image.new("L", (16, 16), color) for color in (0, 255, 128)]
        buffer = BytesIO()
        frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/full-video",
            data=buffer.getvalue(),
            headers={
                "Content-Type": "application/octet-stream",
                "X-Ptasc-Filename": "clip.gif",
                "X-Ptasc-Columns": "4",
                "X-Ptasc-Ramp": "%20%40",
                "X-Ptasc-Invert": "false",
            },
        )
        with urllib.request.urlopen(request) as response:
            assert response.headers["Content-Type"] == "video/mp4"
            assert int(response.headers["X-Frame-Count"]) == 3
            assert response.headers["X-Audio"] == "0"
            render_id = response.headers["X-Render-Id"]
            assert len(response.read()) > 0
        saved = _request(
            port,
            "/api/save-video",
            json.dumps(
                {
                    "filename": "clip.gif",
                    "render_id": render_id,
                    "columns": 4,
                    "ramp": " @",
                    "invert": False,
                }
            ).encode("utf-8"),
        )
        assert saved["frame_count"] == 3
        assert saved["audio"] is False
        stored = list((tmp_path / "data" / "tasks").iterdir())
        assert len(stored) == 1
        assert (stored[0] / "ascii.mp4").stat().st_size > 0
    finally:
        server.shutdown()
        server.server_close()

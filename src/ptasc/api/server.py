"""提供页面和转换接口。只有 serve() 会开始监听。"""

import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ptasc.api.request import parse_convert_payload
from ptasc.api.static_files import content_type, resolve_web_file
from ptasc.audit.log import configure_logs
from ptasc.config.settings import load_settings
from ptasc.jobs import convert_bytes
from ptasc.render import render_image


def make_server(root: Path, host: str, port: int, *, ipv6: bool = False) -> ThreadingHTTPServer:
    web_root = root / "web"
    runtime_log, audit_log = configure_logs(root)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/settings":
                settings = load_settings(root / "configs" / "runtime.yaml")
                self._send_json(
                    200,
                    {
                        "columns": settings.columns,
                        "char_aspect": settings.char_aspect,
                        "ramp": settings.ramp,
                        "invert": settings.invert,
                    },
                )
                return
            target = resolve_web_file(web_root, path)
            if target is None:
                self._send_json(404, {"error": "找不到页面"})
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type(target))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path not in {"/api/convert", "/api/save"}:
                self._send_json(404, {"error": "找不到接口"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
                settings = load_settings(root / "configs" / "runtime.yaml")
                request = parse_convert_payload(payload, settings)
                if path == "/api/convert":
                    preview = render_image(
                        image=request.image,
                        columns=request.columns,
                        char_aspect=request.char_aspect,
                        ramp=request.ramp,
                        invert=request.invert,
                    )
                    body = {
                        "ascii": preview.ascii_art,
                        "columns": preview.columns,
                        "rows": preview.rows,
                    }
                else:
                    result = convert_bytes(
                        root=root,
                        image=request.image,
                        source_name=request.filename,
                        columns=request.columns,
                        char_aspect=request.char_aspect,
                        ramp=request.ramp,
                        invert=request.invert,
                        runtime_log=runtime_log,
                        audit_log=audit_log,
                    )
                    body = {
                        "ascii": result.ascii_art,
                        "columns": result.columns,
                        "rows": result.rows,
                        "task_id": result.task_id,
                    }
            except (ValueError, OSError, json.JSONDecodeError, KeyError) as exc:
                runtime_log.error("%s", exc)
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, body)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, status: int, payload: dict[str, object]) -> None:
            body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class AppServer(ThreadingHTTPServer):
        address_family = socket.AF_INET6 if ipv6 else socket.AF_INET
        allow_reuse_address = False

        def server_bind(self) -> None:
            if ipv6:
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            if sys.platform == "win32":
                exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
                if exclusive is not None:
                    self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
            super().server_bind()

    return AppServer((host, port), Handler)


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = make_server(root, host, port)
    extra = _loopback_v6(root, host, port)
    if extra is not None:
        threading.Thread(target=extra.serve_forever, name="ptasc-ipv6", daemon=True).start()
    try:
        server.serve_forever()
    finally:
        if extra is not None:
            extra.shutdown()
            extra.server_close()
        server.server_close()


def _loopback_v6(root: Path, host: str, port: int) -> ThreadingHTTPServer | None:
    if host not in {"127.0.0.1", "localhost"}:
        return None
    try:
        return make_server(root, "::1", port, ipv6=True)
    except OSError:
        return None

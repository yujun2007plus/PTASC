"""提供页面和转换接口。只有 serve() 会开始监听。"""

import json
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ptasc.api.preview_hold import HeldFrames, PreviewHold
from ptasc.api.render_store import RenderStore, StoredRender
from ptasc.api.request import MAX_FULL_VIDEO_BYTES, parse_convert_payload, parse_full_headers, parse_video_payload
from ptasc.api.static_files import content_type, resolve_web_file
from ptasc.audit.log import configure_logs
from ptasc.config.settings import load_settings
from ptasc.jobs import convert_bytes
from ptasc.render import render_image
from ptasc.render_video import render_prepared
from ptasc.tools.checksum import content_sha256
from ptasc.tools.full_video import render_full_file
from ptasc.tools.video_frames import load_still_frames, read_frames
from ptasc.video_job import convert_video_bytes, save_full_video


def make_server(
    root: Path,
    host: str,
    port: int,
    *,
    ipv6: bool = False,
    hold: PreviewHold | None = None,
    renders: RenderStore | None = None,
) -> ThreadingHTTPServer:
    web_root = root / "web"
    runtime_log, audit_log = configure_logs(root)
    if hold is None:
        hold = PreviewHold()
    if renders is None:
        renders = RenderStore()

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
                        "video_fps": settings.video_fps,
                        "video_max_frames": settings.video_max_frames,
                        "video_max_seconds": settings.video_max_seconds,
                        "video_max_edge": settings.video_max_edge,
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
            if path == "/api/full-video":
                self._render_full()
                return
            if path not in {"/api/convert", "/api/save", "/api/convert-video", "/api/save-video"}:
                self._send_json(404, {"error": "找不到接口"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
                settings = load_settings(root / "configs" / "runtime.yaml")
                if path in {"/api/convert-video", "/api/save-video"}:
                    video_request = parse_video_payload(payload, settings)
                    if path == "/api/save-video" and video_request.render_id and not video_request.video and not video_request.frames:
                        stored = renders.get(video_request.render_id)
                        if stored is None:
                            raise ValueError("完整视频已过期，请重新转换")
                        saved_full = save_full_video(
                            root=root,
                            source_name=video_request.filename,
                            full=stored.video,
                            char_aspect=video_request.char_aspect,
                            ramp=video_request.ramp,
                            invert=video_request.invert,
                            runtime_log=runtime_log,
                            audit_log=audit_log,
                        )
                        body = {
                            "columns": stored.video.columns,
                            "rows": stored.video.rows,
                            "fps": stored.video.fps,
                            "frame_count": stored.video.frame_count,
                            "task_id": saved_full.task_id,
                            "audio": stored.video.has_audio,
                        }
                        self._send_json(200, body)
                        return
                    held, token = _remember_frames(video_request, settings, hold)
                    if path == "/api/convert-video":
                        video_preview = render_prepared(
                            list(held.frames),
                            fps=held.fps,
                            columns=video_request.columns,
                            char_aspect=video_request.char_aspect,
                            ramp=video_request.ramp,
                            invert=video_request.invert,
                            cell_px=settings.video_cell_px,
                            encode=False,
                        )
                        body = {
                            "frames": list(video_preview.frames),
                            "columns": video_preview.columns,
                            "rows": video_preview.rows,
                            "fps": video_preview.fps,
                            "frame_count": len(video_preview.frames),
                            "preview_id": token,
                        }
                    else:
                        saved_video = convert_video_bytes(
                            root=root,
                            video=b"",
                            source_name=video_request.filename,
                            suffix=video_request.suffix,
                            columns=video_request.columns,
                            char_aspect=video_request.char_aspect,
                            ramp=video_request.ramp,
                            invert=video_request.invert,
                            sample_fps=settings.video_fps,
                            max_frames=settings.video_max_frames,
                            max_seconds=settings.video_max_seconds,
                            cell_px=settings.video_cell_px,
                            max_edge=settings.video_max_edge,
                            playback_fps=held.fps,
                            prepared=held.frames,
                            source_sha256=held.digest,
                            runtime_log=runtime_log,
                            audit_log=audit_log,
                        )
                        body = {
                            "columns": saved_video.preview.columns,
                            "rows": saved_video.preview.rows,
                            "fps": saved_video.preview.fps,
                            "frame_count": len(saved_video.preview.frames),
                            "task_id": saved_video.task_id,
                        }
                elif path == "/api/convert":
                    request = parse_convert_payload(payload, settings)
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
                    request = parse_convert_payload(payload, settings)
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

        def _render_full(self) -> None:
            try:
                settings = load_settings(root / "configs" / "runtime.yaml")
                filename, columns, ramp, invert = parse_full_headers(self.headers, settings)
                with tempfile.TemporaryDirectory() as temp:
                    source = Path(temp) / filename
                    _stream_upload(self, source, MAX_FULL_VIDEO_BYTES)
                    full = render_full_file(
                        source,
                        columns=columns,
                        char_aspect=settings.char_aspect,
                        ramp=ramp,
                        invert=invert,
                        sample_fps=settings.video_fps,
                        max_edge=settings.video_max_edge,
                        cell_px=settings.video_cell_px,
                    )
                token = renders.put(StoredRender(video=full, filename=filename))
            except (ValueError, OSError) as exc:
                runtime_log.error("%s", exc)
                self._send_json(400, {"error": str(exc)})
                return
            body = full.mp4
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Render-Id", token)
            self.send_header("X-Columns", str(full.columns))
            self.send_header("X-Rows", str(full.rows))
            self.send_header("X-Fps", str(full.fps))
            self.send_header("X-Frame-Count", str(full.frame_count))
            self.send_header("X-Audio", "1" if full.has_audio else "0")
            self.end_headers()
            self.wfile.write(body)

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


def _stream_upload(handler: BaseHTTPRequestHandler, path: Path, limit: int) -> None:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        raise ValueError("缺少视频数据")
    if length > limit:
        raise ValueError("视频超过 512MB")
    remaining = length
    with path.open("wb") as handle:
        while remaining:
            chunk = handler.rfile.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("视频数据不完整")
            handle.write(chunk)
            remaining -= len(chunk)


def _remember_frames(request, settings, hold: PreviewHold) -> tuple[HeldFrames, str]:
    if request.preview_id and not request.frames and not request.video:
        held = hold.get(request.preview_id)
        if held is None:
            raise ValueError("预览已过期，请重新选择视频")
        return held, request.preview_id
    if request.frames:
        images = load_still_frames(list(request.frames), settings.video_max_edge)
        fps = request.fps
        digest = content_sha256(b"".join(request.frames))
    else:
        images, fps = read_frames(
            request.video,
            request.suffix,
            sample_fps=settings.video_fps,
            max_frames=settings.video_max_frames,
            max_seconds=settings.video_max_seconds,
            max_edge=settings.video_max_edge,
        )
        digest = content_sha256(request.video)
    held = HeldFrames(
        frames=tuple(images),
        fps=fps,
        filename=request.filename,
        digest=digest,
    )
    return held, hold.store(held)


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    hold = PreviewHold()
    renders = RenderStore()
    server = make_server(root, host, port, hold=hold, renders=renders)
    extra = _loopback_v6(root, host, port, hold, renders)
    if extra is not None:
        threading.Thread(target=extra.serve_forever, name="ptasc-ipv6", daemon=True).start()
    try:
        server.serve_forever()
    finally:
        if extra is not None:
            extra.shutdown()
            extra.server_close()
        server.server_close()


def _loopback_v6(
    root: Path,
    host: str,
    port: int,
    hold: PreviewHold,
    renders: RenderStore,
) -> ThreadingHTTPServer | None:
    if host not in {"127.0.0.1", "localhost"}:
        return None
    try:
        return make_server(root, "::1", port, ipv6=True, hold=hold, renders=renders)
    except OSError:
        return None

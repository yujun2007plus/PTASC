"""把 URL 解析成 web 目录里的文件，拒绝跑出该目录。"""

from pathlib import Path
from urllib.parse import unquote

WEB_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
}


def resolve_web_file(web_root: Path, url_path: str) -> Path | None:
    relative = unquote(url_path.split("?", 1)[0]).lstrip("/")
    if relative == "":
        relative = "index.html"
    root = web_root.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate


def content_type(path: Path) -> str:
    return WEB_TYPES.get(path.suffix.lower(), "application/octet-stream")

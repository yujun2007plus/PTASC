"""记住浏览器刚预览过的画面，改参数时不必再上传和解码。"""

import threading
from dataclasses import dataclass
from uuid import uuid4

from PIL import Image


@dataclass(frozen=True)
class HeldFrames:
    frames: tuple[Image.Image, ...]
    fps: float
    filename: str
    digest: str


class PreviewHold:
    def __init__(self, limit: int = 2) -> None:
        self._limit = limit
        self._lock = threading.Lock()
        self._items: dict[str, HeldFrames] = {}
        self._order: list[str] = []

    def store(self, held: HeldFrames) -> str:
        token = uuid4().hex[:16]
        copied = HeldFrames(
            frames=tuple(frame.copy() for frame in held.frames),
            fps=held.fps,
            filename=held.filename,
            digest=held.digest,
        )
        with self._lock:
            self._items[token] = copied
            self._order.append(token)
            while len(self._order) > self._limit:
                self._items.pop(self._order.pop(0), None)
        return token

    def get(self, token: str) -> HeldFrames | None:
        with self._lock:
            held = self._items.get(token)
            if held is None:
                return None
            if token in self._order:
                self._order.remove(token)
                self._order.append(token)
            return held

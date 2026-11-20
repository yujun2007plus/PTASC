"""记住最近一次完整字符视频，保存时不必再传一遍文件。"""

import threading
from dataclasses import dataclass
from uuid import uuid4

from ptasc.tools.full_video import FullVideo


@dataclass(frozen=True)
class StoredRender:
    video: FullVideo
    filename: str


class RenderStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token = ""
        self._item: StoredRender | None = None

    def put(self, item: StoredRender) -> str:
        token = uuid4().hex[:16]
        with self._lock:
            self._token = token
            self._item = item
        return token

    def get(self, token: str) -> StoredRender | None:
        with self._lock:
            if token and token == self._token:
                return self._item
        return None

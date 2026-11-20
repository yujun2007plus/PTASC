"""runtime 记调试和错误，audit 记可复现记录。"""

import logging
from pathlib import Path


def _file_logger(name: str, path: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    resolved = path.resolve()
    for handler in logger.handlers:
        base = getattr(handler, "baseFilename", None)
        if base is not None and Path(base).resolve() == resolved:
            return logger
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def configure_logs(root: Path) -> tuple[logging.Logger, logging.Logger]:
    runtime = _file_logger("ptasc.runtime", root / "logs" / "runtime" / "runtime.log")
    audit = _file_logger("ptasc.audit", root / "logs" / "audit" / "audit.log")
    return runtime, audit

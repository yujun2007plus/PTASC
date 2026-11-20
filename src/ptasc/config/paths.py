"""用 pyproject.toml 和 configs/ 向上查找项目根。"""

from pathlib import Path


def project_root(start: Path | None = None) -> Path:
    origins: list[Path] = []
    if start is not None:
        origins.append(start)
    origins.append(Path.cwd())
    origins.append(Path(__file__).resolve())

    seen: set[Path] = set()
    for origin in origins:
        current = origin.resolve()
        if current.is_file():
            current = current.parent
        for directory in (current, *current.parents):
            if directory in seen:
                continue
            seen.add(directory)
            if (directory / "pyproject.toml").is_file() and (directory / "configs").is_dir():
                return directory
    raise FileNotFoundError("找不到项目根（需要 pyproject.toml 和 configs/）")

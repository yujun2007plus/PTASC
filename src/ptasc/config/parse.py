"""读取扁平 YAML 子集：标量、注释、引号。"""

from pathlib import Path


def _strip_comment(line: str) -> str:
    in_quote = False
    quote = ""
    for index, char in enumerate(line):
        if char in {'"', "'"}:
            if not in_quote:
                in_quote = True
                quote = char
            elif char == quote:
                in_quote = False
        elif char == "#" and not in_quote:
            return line[:index]
    return line


def _parse_scalar(token: str) -> str | int | float | bool:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        return token[1:-1]
    lowered = token.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
        return int(token)
    try:
        if any(mark in token for mark in (".", "e", "E")):
            return float(token)
    except ValueError:
        return token
    return token


def parse_yaml_subset(text: str) -> dict[str, str | int | float | bool]:
    values: dict[str, str | int | float | bool] = {}
    for raw in text.splitlines():
        line = _strip_comment(raw).strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"无法解析配置行: {raw}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"无法解析配置行: {raw}")
        values[key] = _parse_scalar(raw_value.strip())
    return values


def load_yaml_subset(path: Path) -> dict[str, str | int | float | bool]:
    return parse_yaml_subset(path.read_text(encoding="utf-8"))

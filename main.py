"""把一张图片转换成字符画，并写入单独的任务目录。"""

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ptasc.audit.log import configure_logs
from ptasc.config.paths import project_root
from ptasc.config.settings import load_settings
from ptasc.jobs import convert_bytes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把图片转换成字符画")
    parser.add_argument("image", nargs="?", type=Path, help="输入图片路径")
    parser.add_argument("--columns", type=int, help="覆盖配置中的列数")
    parser.add_argument("--output", type=Path, help="另外保存一份字符画的路径")
    parser.add_argument("--web", action="store_true", help="打开浏览器页面")
    parser.add_argument("--host", default="127.0.0.1", help="页面监听地址")
    parser.add_argument("--port", type=int, default=8765, help="页面监听端口")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = project_root(Path(__file__).resolve().parent)
    except FileNotFoundError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    if args.web:
        from ptasc.api.server import serve

        url = f"http://{args.host}:{args.port}"
        sys.stdout.write(f"页面地址: {url}\n")
        sys.stdout.flush()
        try:
            serve(root, args.host, args.port)
        except OSError as exc:
            sys.stderr.write(f"无法启动页面: {exc}\n")
            return 1
        return 0

    if args.image is None:
        sys.stderr.write("请提供图片路径，或使用 --web 打开页面\n")
        return 1

    runtime_log, audit_log = configure_logs(root)
    try:
        settings = load_settings(root / "configs" / "runtime.yaml")
        columns = settings.columns if args.columns is None else args.columns
        if isinstance(columns, bool) or not isinstance(columns, int) or columns < 1:
            raise ValueError("列数必须是正整数")
        image_path = args.image.expanduser().resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"找不到图片: {image_path}")

        result = convert_bytes(
            root=root,
            image=image_path.read_bytes(),
            source_name=image_path.name,
            columns=columns,
            char_aspect=settings.char_aspect,
            ramp=settings.ramp,
            invert=settings.invert,
            runtime_log=runtime_log,
            audit_log=audit_log,
        )
        if args.output is not None:
            destination = args.output.expanduser()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(result.ascii_art, encoding="utf-8")
        sys.stdout.write(result.ascii_art)
        return 0
    except (OSError, ValueError, FileNotFoundError) as exc:
        runtime_log.error("%s", exc)
        sys.stderr.write(f"{exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

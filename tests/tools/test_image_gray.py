from PIL import Image

from ptasc.tools.image_gray import load_grayscale


def test_load_grayscale_converts_color(tmp_path):
    path = tmp_path / "color.png"
    Image.new("RGB", (2, 2), color=(0, 255, 0)).save(path)

    gray = load_grayscale(path)

    assert gray.mode == "L"
    assert gray.size == (2, 2)
    assert 140 <= gray.getpixel((0, 0)) <= 160

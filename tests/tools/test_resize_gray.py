from PIL import Image

from ptasc.tools.resize_gray import character_rows, resize_gray


def test_square_image_uses_half_as_many_rows():
    assert character_rows(640, 640, 32, 2.0) == 16


def test_wide_image_keeps_its_proportions():
    assert character_rows(100, 50, 100, 2.0) == 25


def test_resize_gray_matches_character_rows():
    image = Image.new("L", (40, 20), color=128)
    fitted = resize_gray(image, columns=20, char_aspect=2.0)

    assert fitted.size == (20, 5)

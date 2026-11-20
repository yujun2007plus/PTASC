from PIL import Image

from ptasc.tools.pixels_to_ascii import pixels_to_ascii


def test_contrast_uses_the_real_range():
    image = Image.new("L", (2, 1))
    image.putpixel((0, 0), 10)
    image.putpixel((1, 0), 20)

    assert pixels_to_ascii(image, " .@", invert=False) == "@ \n"


def test_fixed_scale_does_not_stretch_a_narrow_range():
    image = Image.new("L", (2, 1))
    image.putpixel((0, 0), 10)
    image.putpixel((1, 0), 20)

    assert pixels_to_ascii(image, " .@", invert=False, stretch=False) == "..\n"


def test_invert_maps_bright_pixels_to_dense_characters():
    image = Image.new("L", (2, 1))
    image.putpixel((0, 0), 0)
    image.putpixel((1, 0), 255)

    assert pixels_to_ascii(image, " .@", invert=True) == " @\n"

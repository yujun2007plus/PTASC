"""把灰度像素按亮度映射到字符坡道。"""

from PIL import Image


def pixels_to_ascii(image: Image.Image, ramp: str, invert: bool) -> str:
    if not ramp:
        raise ValueError("字符坡道不能为空")
    gray = image if image.mode == "L" else image.convert("L")
    read_pixels = getattr(gray, "get_flattened_data", gray.getdata)
    pixels = list(read_pixels())
    if not pixels:
        raise ValueError("图片没有像素")
    low = min(pixels)
    high = max(pixels)
    span = high - low or 1
    last = len(ramp) - 1
    width, height = gray.size
    lines: list[str] = []
    for y in range(height):
        start = y * width
        chars: list[str] = []
        for value in pixels[start : start + width]:
            brightness = (value - low) / span
            position = brightness if invert else 1 - brightness
            index = int(position * last)
            index = max(0, min(last, index))
            chars.append(ramp[index])
        lines.append("".join(chars))
    return "\n".join(lines) + "\n"

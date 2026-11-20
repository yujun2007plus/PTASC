from ptasc.tools.ascii_canvas import paint_frame


def test_different_symbols_share_one_cell_and_keep_the_source_shape():
    dots = paint_frame("....", invert=False, cell_px=16, char_aspect=2.0)
    dense = paint_frame("@@@@", invert=False, cell_px=16, char_aspect=2.0)
    square = paint_frame("\n".join(["@@@@@@@@"] * 4), invert=False, cell_px=16, char_aspect=2.0)

    assert dots.size == dense.size
    assert abs(square.width / square.height - 1) < 0.08

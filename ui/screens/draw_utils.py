import math

def draw_progress_bar(draw, x_tl, y_tl, x_br, y_br, h_padding, v_padding, progress):
    """Draw a bordered progress bar filled to the supplied fractional progress."""
    container_coords = (x_tl, y_tl, x_br, y_br)
    bar_coords = (x_tl + h_padding,
                  y_tl + v_padding,
                  math.floor(x_tl + h_padding + progress * (x_br - x_tl - h_padding)),
                  y_br - v_padding)
    draw.rectangle(container_coords, outline=255)
    draw.rectangle(bar_coords, fill=255)

from pathlib import Path

from PIL import Image


WIDTH = 128
HEIGHT = 64
BUTTON_NAMES = ("A", "B", "L", "R", "U", "D", "C")
CAT_IMAGE = Path(__file__).with_name("happycat_oled_64.ppm")


def load_cat_image():
    """Load the optional monochrome cat image, returning None when absent."""
    if CAT_IMAGE.exists():
        return Image.open(CAT_IMAGE).convert("1")
    return None


def new_frame():
    """Create a blank 1-bit image sized for the OLED display."""
    return Image.new("1", (WIDTH, HEIGHT))

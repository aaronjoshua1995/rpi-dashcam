from PIL import Image, ImageDraw, ImageChops

from ..display import HEIGHT, WIDTH, new_frame
from .base import Screen
from .draw_utils import draw_progress_bar

class SplashScreen(Screen):
    """Render the application title, status message, and startup progress."""

    def __init__(self):
        """Initialize an empty status message and zero progress."""
        self.progress = 0.0
        self.status_text = ""

    def set_status(self, status: str):
        """Set the status text displayed in the center of the splash screen."""
        self.status_text = status

    def set_progress(self, progress: float):
        """Set the fractional progress value used by the progress bar."""
        self.progress = progress

    def update(self, elapsed: float, pressed: dict[str, bool]) -> None:
        """Advance the automatic splash progress using elapsed time."""
        if self.progress < 100.0:
            self.progress = min(self.progress + elapsed * 0.04, 1)

    def render(self, pressed: dict[str, bool]) -> Image.Image:
        """Render the splash frame as a monochrome OLED image."""
        image = new_frame()
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=255)
        draw.text((6, 6), "RPI-DASHCAM", fill=255)
        draw.text((122, 48), "v0.0.1", anchor="ra", fill=255)
        draw_progress_bar(draw, 6, 26, 121, 38, 2, 2, self.progress)
        text_mask = Image.new("1", image.size, 0)
        text_draw = ImageDraw.Draw(text_mask)
        text_draw.text((64, 32), self.status_text, fill=255, anchor="mm")
        image = ImageChops.logical_xor(image, text_mask)
        return image

from backend import BackendServiceInterface
from PIL import Image, ImageDraw

from ..display import HEIGHT, WIDTH, new_frame
from .base import Screen
from .draw_utils import draw_progress_bar


class SystemStatusScreen(Screen):
    """Display periodically refreshed CPU, memory, disk, and temperature data."""

    def __init__(self, backend: BackendServiceInterface):
        """Load initial system statistics and reset the refresh timer."""
        self.backend = backend
        self.stats = backend.get_system_stats()
        self.stats_refresh_elapsed = 0.0

    def update(self, elapsed: float, pressed: dict[str, bool]) -> None:
        """Refresh system statistics at most once per second."""
        self.stats_refresh_elapsed += elapsed
        if self.stats_refresh_elapsed >= 1.0:
            self.stats = self.backend.get_system_stats()
            self.stats_refresh_elapsed = 0.0

    def __get_stats(self):
        """Return the displayed statistic labels and values."""
        return {
            "CPU": self.stats.cpu_percent,
            "MEM" : self.stats.memory_percent,
            "DISK" : self.stats.disk_percent,
            "TEMP": self.stats.temperature_celsius,
        }

    def render(self, pressed: dict[str, bool]) -> Image.Image:
        """Render system statistics as text and progress bars."""
        image = new_frame()
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=255)

        i = 0
        for key, val in self.__get_stats().items():
            y = 6 + (i * 12)
            draw.text((6, y), key, fill=255)
            if key == "TEMP":
                draw.text((39, y), f"{val}°C", fill=255)
            else:
                val = max(0, min(val, 1.0))
                draw_progress_bar(draw, 39, y + 1, 124, y + 10, 1, 1, val)
            i += 1

        return image

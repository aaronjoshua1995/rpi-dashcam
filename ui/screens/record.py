
import math

from backend import BackendServiceInterface
from PIL import Image, ImageDraw

from ..display import WIDTH, HEIGHT, new_frame
from .base import Screen


class RecordScreen(Screen):
    """Display recording status and rotate sessions with the B button."""

    def __init__(self, backend: BackendServiceInterface):
        """Start the default recording session and initialize button state."""
        self.backend = backend
        self.backend.start_recording()
        self.status = self.backend.get_recording_status()
        self.last_b_pressed = False

    def update(self, elapsed: float, pressed: dict[str, bool]) -> None:
        """Rotate once for each new B-button press and refresh status."""
        if pressed["B"] and not self.last_b_pressed:
            self.backend.rotate_recording()
        self.last_b_pressed = pressed["B"]
        self.status = self.backend.get_recording_status()

    def __recording_time(self):
        """Format the current recording duration as hours, minutes, and milliseconds."""
        divisors = [3600, 60, 1]
        remaining_time = self.status.duration_seconds
        ts = []
        for d in divisors:
            t = math.floor(remaining_time / d)
            remaining_time = remaining_time - (t * d)
            ts.append(t)
        ts.append(math.floor(remaining_time * 1000))
        return f"{ts[0]:02}:{ts[1]:02}:{ts[2]:02}.{ts[3]:03}"
        
    def render(self, pressed: dict[str, bool]) -> Image.Image:
        """Render the recording title, duration, and active/error indicator."""
        image = new_frame()
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=255)
        draw.text((6, 6), "RECORD", fill=255)
        draw.text((122, 6), self.__recording_time(), fill=255, anchor="ra")
        # Indicate whether recording is on or off
        draw.text((6, 48), "[ON]" if self.status.recording else "[ERR]", fill=255)
        return image

import math

from PIL import Image, ImageDraw, ImageOps

from backend import BackendServiceInterface
from ..display import WIDTH, HEIGHT, new_frame
from .base import Screen
from .warning_dialog import WarningDialog

class LibraryScreen(Screen):
    """Display recordings and provide button-driven deletion confirmation."""

    def __init__(self, backend: BackendServiceInterface):
        """Load the initial recording list and initialize selection state."""
        self.backend = backend
        self.recordings = self.backend.list_recordings()
        self.scroll = 0.0
        self.selected_idx = 0
        self.last_pressed = None
        self.show_delete_confirm = False
        self.warning_dialog = WarningDialog("Delete?")

    def update(self, elapsed: float, pressed: dict[str, bool]) -> None:
        """Refresh recordings and process navigation or deletion input."""
        self.scroll += elapsed * 0.1
        if self.scroll > 1.0:
            self.scroll = 0.0

        self.recordings = self.backend.list_recordings()
        if len(self.recordings) == 0:
            return

        if not self.show_delete_confirm:
            if pressed["D"] and self.last_pressed != "D":
                self.selected_idx = (self.selected_idx + 1) % len(self.recordings)
                self.last_pressed = "D"
            elif pressed["U"] and self.last_pressed != "U":
                self.selected_idx = (self.selected_idx - 1) % len(self.recordings)
                self.last_pressed = "U"
            elif pressed["A"] and self.last_pressed != "A":
                self.show_delete_confirm = True
            elif pressed["B"] and self.last_pressed != "B":
                self.show_delete_confirm = False
            else:
                self.last_pressed = None
        else:
            self.warning_dialog.update(pressed)
            if pressed["B"] and self.last_pressed != "B":
                if self.warning_dialog.get_option():
                    print(f"Delete recording: {self.recordings[self.selected_idx].id}")
                    self.backend.delete_recording(self.recordings[self.selected_idx].id)
                self.show_delete_confirm = False
            else:
                self.last_pressed = None

    def __draw_scroll_text(self, text, w, h, scroll):
        """Render clipped text into a small scrolling list-cell image."""
        image = Image.new("1", (w, h))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, w - 1, h - 1), outline=255)
        draw.text((-math.floor(scroll * (w - 2)) + 2, 0), text, fill=255)
        return image

    def render(self, pressed: dict[str, bool]) -> Image.Image:
        """Render the recording list, selection marker, and optional dialog."""
        image = new_frame()
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=255)
        for i, r in enumerate(self.recordings):
            scroll_txt = self.__draw_scroll_text(r.stem, 121, 12, 0.0)
            if self.selected_idx == i:
                scroll_txt = ImageOps.invert(scroll_txt)
            image.paste(scroll_txt, (0, max(i*12-i, 0)))

        draw.rectangle((WIDTH - 8, 0, WIDTH - 1, HEIGHT - 1), outline=255)
        draw.polygon([(123, 1), (127, 6), (120, 6), (124, 1)], fill=255)
        draw.polygon([(123, HEIGHT-1-1), (127, HEIGHT-1-6), (120, HEIGHT-1-6), (124, HEIGHT-1-1)], fill=255)

        if self.show_delete_confirm:
            wd = self.warning_dialog.render()
            image.paste(wd, (WIDTH//4, HEIGHT//4))
        
        return image

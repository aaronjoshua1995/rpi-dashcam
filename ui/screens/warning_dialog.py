from PIL import Image, ImageDraw

class WarningDialog():
    """Render a two-option confirmation dialog controlled by up/down buttons."""

    def __init__(self, text):
        """Create a dialog with the supplied prompt and the NO option selected."""
        self.text = text
        self.last_pressed = None
        self.option = False

    def get_option(self):
        """Return whether the affirmative option is currently selected."""
        return self.option

    def reset(self):
        """Reset the selected option to NO."""
        self.option = False

    def update(self, pressed: dict[str, bool]) -> None:
        """Toggle the selected option when a new up or down press arrives."""
        if pressed["D"] and self.last_pressed != "L":
            self.option = not self.option
            self.last_pressed = "L"
        elif pressed["U"] and self.last_pressed != "R":
            self.option = not self.option
            self.last_pressed = "R"
        else:
            self.last_pressed = None

    def render(self) -> Image.Image:
        """Render the prompt and current YES/NO selection as a monochrome image."""
        image = Image.new("1", (64, 32))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 64 - 1, 32 - 1), fill=255)
        draw.rectangle((2, 2, 64 - 3, 32 - 3), outline=0)
        draw.text((6, 2), self.text, fill=0)
        if self.option:
            draw.text((6, 16), "[YES]", fill=0)
            draw.text((58, 16), "NO", fill=0, anchor="ra")
        else:
            draw.text((6, 16), "YES", fill=0)
            draw.text((58, 16), "[NO]", fill=0, anchor="ra")
        return image

from abc import ABC, abstractmethod

from PIL import Image


class Screen(ABC):
    """Contract implemented by every OLED screen."""

    @abstractmethod
    def update(self, elapsed: float, pressed: dict[str, bool]) -> None:
        """Advance screen state by elapsed seconds and current button input."""

    @abstractmethod
    def render(self, pressed: dict[str, bool]) -> Image.Image:
        """Return the current 1-bit OLED frame for the current button input."""

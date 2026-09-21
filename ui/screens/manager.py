from backend import BackendServiceInterface

from .base import Screen
from .record import RecordScreen
from .splash import SplashScreen
from .system_status import SystemStatusScreen
from .library import LibraryScreen

class ScreenManager:
    """Own the registered screens and route navigation, updates, and rendering."""

    def __init__(self, backend: BackendServiceInterface):
        """Create the screen registry using the shared backend service."""
        self.backend = backend
        self.screens: list[Screen] = [
            RecordScreen(backend),
            LibraryScreen(backend),
            # SplashScreen(),
            SystemStatusScreen(backend),
        ]
        self.index = 0

    @property
    def current(self) -> Screen:
        """Return the currently selected screen instance."""
        return self.screens[self.index]

    @property
    def position(self) -> str:
        """Return a compact display label for the current screen position."""
        return f"{self.index + 1}/{len(self.screens)} {type(self.current).__name__}"

    def next(self) -> None:
        """Advance to the next registered screen, wrapping at the end."""
        self.index = (self.index + 1) % len(self.screens)

    def previous(self) -> None:
        """Move to the previous registered screen, wrapping at the beginning."""
        self.index = (self.index - 1) % len(self.screens)

    def update(self, elapsed: float, pressed: dict[str, bool]) -> None:
        """Forward timing and button input to the current screen."""
        self.current.update(elapsed, pressed)

    def render(self, pressed: dict[str, bool]):
        """Return the current screen's rendered OLED image."""
        return self.current.render(pressed)

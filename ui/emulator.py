import time
import tkinter as tk
import sys

from PIL import ImageTk

from backend import BackendService, BackendServiceInterface

from .display import BUTTON_NAMES, HEIGHT, WIDTH
from .screens import ScreenManager


DISPLAY_SCALE = 6
FRAME_INTERVAL_MS = round(1000 / 60)
KEY_MAP = {
    "a": "A",
    "b": "B",
    "Left": "L",
    "Right": "R",
    "Up": "U",
    "Down": "D",
    "space": "C",
    "Return": "C",
}


def run_emulator(backend: BackendServiceInterface | None = None):
    """Run the desktop Tk emulator using the shared screen manager."""
    root = tk.Tk()
    root.title("OLED Bonnet Emulator")
    root.configure(background="#202020")
    root.resizable(False, False)
    canvas = tk.Canvas(root, width=WIDTH * DISPLAY_SCALE, height=HEIGHT * DISPLAY_SCALE,
                       background="#101010", highlightthickness=0)
    canvas.pack(padx=16, pady=16)
    status = tk.Label(root, text="Arrows: buttons    A/B: face buttons    Tab: next screen",
                      background="#202020", foreground="#eeeeee")
    status.pack(pady=(0, 12))

    pressed = {name: False for name in BUTTON_NAMES}
    backend = backend or BackendService()
    manager = ScreenManager(backend)
    last_time = time.monotonic()

    def show_screen():
        """Update the emulator status label with the active screen position."""
        status.configure(text=f"Screen {manager.position}")

    def handle_tab(_event, backwards=False):
        """Navigate screens in response to Tab or Shift-Tab."""
        if backwards:
            manager.previous()
        else:
            manager.next()
        show_screen()
        return "break"

    def handle_key(event, is_pressed):
        """Translate a Tk key event into the shared button-state mapping."""
        name = KEY_MAP.get(event.keysym)
        if name is not None:
            pressed[name] = is_pressed
            status.configure(text=f"Pressed: {name}" if is_pressed else "Ready")

    def refresh():
        """Advance, render, and schedule the next emulator frame."""
        nonlocal last_time
        now = time.monotonic()
        elapsed = min(now - last_time, 0.1)
        last_time = now
        try:
            manager.update(elapsed, pressed)
            frame = manager.render(pressed).resize((WIDTH * DISPLAY_SCALE, HEIGHT * DISPLAY_SCALE))
        except Exception as error:
            print(f"Skipping frame after error: {error}", file=sys.stderr)
            root.after(FRAME_INTERVAL_MS, refresh)
            return
        photo = ImageTk.PhotoImage(frame)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas.image = photo
        root.after(FRAME_INTERVAL_MS, refresh)

    root.bind_all("<KeyPress>", lambda event: handle_key(event, True))
    root.bind_all("<KeyRelease>", lambda event: handle_key(event, False))
    canvas.bind("<KeyPress-Tab>", handle_tab)
    canvas.bind("<KeyRelease-Tab>", lambda event: "break")
    canvas.bind("<Shift-KeyPress-Tab>", lambda event: handle_tab(event, backwards=True))
    canvas.bind("<Shift-KeyRelease-Tab>", lambda event: "break")
    root.after(100, canvas.focus_force)
    try:
        refresh()
        root.mainloop()
    except KeyboardInterrupt:
        print("Stopping emulator...", file=sys.stderr)
    finally:
        try:
            backend.stop_recording()
        except Exception as error:
            print(f"Could not stop recording cleanly: {error}", file=sys.stderr)
        root.destroy()

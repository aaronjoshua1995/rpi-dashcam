import time
import sys

from backend import BackendService, BackendServiceInterface

from .display import HEIGHT, WIDTH
from .screens import ScreenManager


FRAME_INTERVAL_SECONDS = 1 / 60


def run_hardware(backend: BackendServiceInterface | None = None):
    """Run the physical OLED and GPIO button loop on Raspberry Pi hardware."""
    import adafruit_ssd1306
    import board
    import busio
    from digitalio import DigitalInOut, Direction, Pull

    i2c = busio.I2C(board.SCL, board.SDA)
    display = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)
    pins = {
        "A": board.D5,
        "B": board.D6,
        "L": board.D27,
        "R": board.D23,
        "U": board.D17,
        "D": board.D22,
        "C": board.D4,
    }
    buttons = {}
    for name, pin in pins.items():
        button = DigitalInOut(pin)
        button.direction = Direction.INPUT
        button.pull = Pull.UP
        buttons[name] = button

    backend = backend or BackendService()
    manager = ScreenManager(backend)
    previous = {name: False for name in buttons}
    last_time = time.monotonic()
    display.fill(0)
    display.show()
    try:
        while True:
            now = time.monotonic()
            elapsed = min(now - last_time, 0.1)
            last_time = now
            pressed = {name: not button.value for name, button in buttons.items()}
            if pressed["L"] and not previous["L"]:
                manager.next()
            if pressed["R"] and not previous["R"]:
                manager.previous()
            previous = pressed.copy()
            try:
                manager.update(elapsed, pressed)
                display.image(manager.render(pressed))
                display.show()
            except Exception as error:
                print(f"Skipping frame after error: {error}", file=sys.stderr)
            time.sleep(FRAME_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Stopping UI...", file=sys.stderr)
    finally:
        try:
            backend.stop_recording()
        except Exception as error:
            print(f"Could not stop recording cleanly: {error}", file=sys.stderr)
        try:
            display.fill(0)
            display.show()
        finally:
            for button in buttons.values():
                button.deinit()
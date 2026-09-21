import argparse
import signal

from backend import BackendService

from .emulator import run_emulator
from .hardware import run_hardware


def _handle_sigterm(_signum, _frame):
    """Convert SIGTERM into KeyboardInterrupt for shared shutdown handling."""
    raise KeyboardInterrupt


def main():
    """Parse command-line options and launch hardware or emulator mode."""
    parser = argparse.ArgumentParser(description="Run the OLED bonnet example")
    parser.add_argument(
        "--emulate",
        action="store_true",
        help="run a desktop OLED emulator instead of using Raspberry Pi hardware",
    )
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, _handle_sigterm)
    backend = BackendService()
    if args.emulate:
        run_emulator(backend)
    else:
        run_hardware(backend)


if __name__ == "__main__":
    main()
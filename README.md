# Raspberry Pi Dashcam

This project is a Python program that turns your Raspberry Pi into a dashcam. It was designed for the Raspberry Pi Zero 2W with a Adafruit Camera Module 3 Wide NOIR camera and 128x64 SSD1306 OLED bonnet.

The hardware mode is intended to run on the Raspberry Pi connected to the bonnet. The desktop emulator can be used on a regular development PC without GPIO or I2C hardware.

## Requirements

- Python 3
- `python3-venv` installed so the virtual environment can be created
- Tk installed to run the desktop emulator

For the Raspberry Pi hardware mode, you also need an OLED bonnet connected to the GPIO header and I2C enabled.

### Ubuntu development PC

Install Python, virtual-environment support, Tk, and the native headers used by some Python dependencies:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev python3-tk
```

### Arch Linux development PC

On Arch, the `python` package includes Python 3 and virtual-environment support. Install it together with pip and Tk:

```bash
sudo pacman -Syu --needed python python-pip tk
```

The emulator does not require GPIO or I2C packages on the development PC. Those are only needed on the Raspberry Pi; Raspberry Pi OS users should also install `libgpiod2`:

Install the system prerequisites on Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev python3-tk libgpiod2
```

Python packages are listed in [requirements.txt](requirements.txt), so the environment can be recreated without guessing which libraries are needed.

## Setup

On Raspberry Pi OS, install the system and Python dependencies with:

```bash
./install_pi.sh
```

The script creates `.venv` with access to the system GStreamer Python
bindings, installs the project requirements, and creates the recordings
directory. It must be run on the Pi and does not replace enabling I2C with
`raspi-config`.

From the project directory, run:

```bash
./setup_venv.sh
source .venv/bin/activate
```

The setup script creates `.venv` when needed and installs every package from `requirements.txt`. The virtual environment is ignored by Git and can be safely recreated.

To set up manually instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

With the virtual environment active:

```bash
python main.py
```

The same UI entry point can also be run as a package:

```bash
python -m ui.main
```

## Desktop emulator

The emulator uses the same drawing logic but replaces the OLED and GPIO inputs with a desktop window. It is useful for testing the display layout on a development PC without Raspberry Pi hardware:

```bash
python main.py --emulate
```

The emulator controls are:

- Arrow keys: Up, Down, Left, and Right
- `A` and `B`: face buttons
- Space or Enter: center button
- `Tab`: next screen
- `Shift+Tab`: previous screen

The emulator targets 60 frames per second. The buttons are pressed while a key is held and released when the key is released. The hardware dependencies remain lazy-loaded, so emulator mode does not try to access I2C or GPIO.

Click the emulator window once if your desktop has not focused it automatically. The status line shows the button currently being received, and the corresponding OLED shape is filled while the key is held.

## Project layout

- `main.py`: root command-line launcher for the UI
- `ui/`: display application
- `ui/main.py`: UI command-line entry point
- `ui/display.py`: shared OLED dimensions, image loading, and frame helpers
- `ui/screens/`: screen package and screen registry
- `ui/hardware.py`: Raspberry Pi GPIO, SSD1306 output, and physical screen navigation
- `ui/emulator.py`: desktop Tk window, keyboard input, and animation clock
- `backend/__init__.py`: public backend exports
- `backend/interface.py`: `BackendServiceInterface` consumed by the UI
- `backend/models.py`: shared recording and system-stat data models
- `backend/service.py`: `BackendService` facade and function composition
- `backend/record.py`: `RecordFunction` scaffold
- `backend/system.py`: `SystemFunction` scaffold
- `backend/library.py`: `LibraryFunction` scaffold

## Raspberry Pi configuration

Enable I2C with:

```bash
sudo raspi-config
```

Select **Interface Options**, then **I2C**, enable it, and reboot if prompted. You can check that the bonnet is visible with:

```bash
sudo apt install -y i2c-tools
sudo i2cdetect -y 1
```

## Updating dependencies

When a dependency changes, update [requirements.txt](requirements.txt), then reinstall into the active environment:

```bash
python -m pip install -r requirements.txt --upgrade
```
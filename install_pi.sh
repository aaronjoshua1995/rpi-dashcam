#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${project_dir}/.venv"

if [[ "$(uname -m)" != "aarch64" && "$(uname -m)" != "armv7l" ]]; then
    echo "Warning: this script is intended for Raspberry Pi OS." >&2
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get is required. Run this script on Raspberry Pi OS." >&2
    exit 1
fi

sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-tk \
    python3-gi \
    python3-gst-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-libcamera \
    ffmpeg \
    libgpiod2 \
    i2c-tools

if [[ ! -d "${venv_dir}" ]]; then
    python3 -m venv --system-site-packages "${venv_dir}"
fi

"${venv_dir}/bin/python" -m pip install --upgrade pip
"${venv_dir}/bin/python" -m pip install -r "${project_dir}/requirements.txt"

recordings_owner="${SUDO_USER:-${USER}}"
recordings_group="$(id -gn "${recordings_owner}")"
sudo install -d -o "${recordings_owner}" -g "${recordings_group}" -m 0755 \
  /usr/share/rpi-dashcam/recordings

cat <<EOF

Installation complete.

Activate the environment with:
  source "${venv_dir}/bin/activate"

Run the hardware UI with:
  python "${project_dir}/main.py"

Before running, enable I2C with:
  sudo raspi-config
EOF

#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${project_dir}/.venv"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required. Install it with your system package manager." >&2
    exit 1
fi

if [[ ! -d "${venv_dir}" ]]; then
    python3 -m venv "${venv_dir}"
fi

"${venv_dir}/bin/python" -m pip install --upgrade pip
"${venv_dir}/bin/python" -m pip install -r "${project_dir}/requirements.txt"

echo
echo "Environment ready. Activate it with:"
echo "  source ${venv_dir}/bin/activate"
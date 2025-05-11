# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 igo95862
from __future__ import annotations

from shutil import which
from subprocess import run

from .base import PROJECT_ROOT_PATH

VENV_DIR = PROJECT_ROOT_PATH / "venv"


def setup_venv() -> None:
    if VENV_DIR.exists():
        print("venv dir already exists, skipping...")
        return

    python_bin = which("python3")
    if python_bin is None:
        print("Python not found")
        raise SystemExit(1)

    run(
        args=(
            python_bin,
            "-m",
            "venv",
            "--system-site-packages",
            str(VENV_DIR),
        ),
        check=True,
    )


def setup_editable_install() -> None:
    run(
        args=(
            str(VENV_DIR / "bin/pip"),
            "install",
            "--no-build-isolation",
            "--config-settings=editable-verbose=true",
            "--config-settings=setup-args=-Dman=false",
            "--config-settings=setup-args=-Duse-vendored-python-lxns=enabled",
            "--config-settings=install-args=--tags=runtime",
            "--editable",
            str(PROJECT_ROOT_PATH),
        ),
        check=True,
    )


def main() -> None:
    setup_venv()
    setup_editable_install()


if __name__ == "__main__":
    main()

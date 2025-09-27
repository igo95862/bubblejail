# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 igo95862
from __future__ import annotations

from subprocess import run

from .base import PROJECT_ROOT_PATH, PYTHON_SOURCES


def format_with_black(check: bool = False) -> None:
    black_args = ["black"]

    if check:
        black_args.extend(("--check", "--diff"))

    black_args.extend(map(str, PYTHON_SOURCES))

    run(
        args=black_args,
        cwd=PROJECT_ROOT_PATH,
        check=check,
    )


def format_with_isort(check: bool = False) -> None:
    isort_args = ["isort", "--profile", "black"]

    if check:
        isort_args.extend(("--check", "--diff"))

    isort_args.extend(map(str, PYTHON_SOURCES))

    run(
        args=isort_args,
        cwd=PROJECT_ROOT_PATH,
        check=check,
    )


def format_meson(check: bool = False) -> None:
    meson_args = [
        "meson",
        "format",
        "--configuration",
        str(PROJECT_ROOT_PATH / "meson.format"),
        "--recursive",
    ]

    if check:
        meson_args.append("--check")
    else:
        meson_args.append("--inplace")

    run(
        args=meson_args,
        cwd=PROJECT_ROOT_PATH,
        check=check,
    )


if __name__ == "__main__":
    format_with_isort()
    format_with_black()
    format_meson()

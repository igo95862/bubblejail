# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 igo95862
from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, run
from sys import stderr

from .base import BUILD_DIR, PROJECT_ROOT_PATH, PYTHON_SOURCES
from .run_format import format_with_black, format_with_isort

LXNS_SUBPROJECT_PYTHON_SOURCE = PROJECT_ROOT_PATH / "subprojects/python-lxns/src/"


def run_linter(args: list[str | Path]) -> bool:
    print("Running:", args[0], file=stderr)
    try:
        run(
            args=args,
            cwd=PROJECT_ROOT_PATH,
            check=True,
        )
    except CalledProcessError:
        return True

    return False


def run_pyflakes() -> bool:
    return run_linter(["pyflakes", *PYTHON_SOURCES])


def run_mypy() -> bool:
    cache_dir = BUILD_DIR / "mypy_cache"
    mypy_args: list[str | Path] = [
        "mypy",
        "--pretty",
        "--strict",
        "--cache-dir",
        cache_dir,
        "--ignore-missing-imports",
        *PYTHON_SOURCES,
    ]
    if LXNS_SUBPROJECT_PYTHON_SOURCE.exists():
        mypy_args.append(LXNS_SUBPROJECT_PYTHON_SOURCE)

    return run_linter(mypy_args)


def run_reuse() -> bool:
    return run_linter(["reuse", "lint"])


def run_black() -> bool:
    print("Running: black", file=stderr)
    try:
        format_with_black(check=True)
    except CalledProcessError:
        return True

    return False


def run_isort() -> bool:
    print("Running: isort", file=stderr)
    try:
        format_with_isort(check=True)
    except CalledProcessError:
        return True

    return False


def main() -> None:
    BUILD_DIR.mkdir(exist_ok=True)

    has_failed = False

    has_failed |= run_pyflakes()
    has_failed |= run_mypy()
    has_failed |= run_reuse()
    has_failed |= run_black()
    has_failed |= run_isort()

    if has_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

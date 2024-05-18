# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 igo95862
from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, run

PROJECT_ROOT_PATH = Path(__file__).parent.parent
BUILD_DIR = PROJECT_ROOT_PATH / "build"
PYTHON_SOURCES: list[Path] = [
    PROJECT_ROOT_PATH / "src",
    PROJECT_ROOT_PATH / "tools",
    PROJECT_ROOT_PATH / "test",
    PROJECT_ROOT_PATH / "docs/man_generator.py",
]
LXNS_SUBPROJECT_PYTHON_SOURCE = (
    PROJECT_ROOT_PATH / "subprojects/python-lxns/src/"
)


def run_linter(args: list[str | Path]) -> bool:
    print("Running:", args[0])
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
        "--cache-dir", cache_dir,
        "--ignore-missing-imports",
        *PYTHON_SOURCES
    ]
    if LXNS_SUBPROJECT_PYTHON_SOURCE.exists():
        mypy_args.append(LXNS_SUBPROJECT_PYTHON_SOURCE)

    return run_linter(
        mypy_args
    )


def run_reuse() -> bool:
    return run_linter(["reuse", "lint"])


def main() -> None:
    BUILD_DIR.mkdir(exist_ok=True)

    has_failed = False

    has_failed |= run_pyflakes()
    has_failed |= run_mypy()
    has_failed |= run_reuse()

    if has_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

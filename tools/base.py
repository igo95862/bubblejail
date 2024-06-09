# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 igo95862
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT_PATH = Path(__file__).parent.parent
BUILD_DIR = PROJECT_ROOT_PATH / "build"
PYTHON_SOURCES: list[Path] = [
    PROJECT_ROOT_PATH / "src",
    PROJECT_ROOT_PATH / "tools",
    PROJECT_ROOT_PATH / "test",
    PROJECT_ROOT_PATH / "docs/man_generator.py",
]

__all__ = ("PROJECT_ROOT_PATH", "BUILD_DIR", "PYTHON_SOURCES")

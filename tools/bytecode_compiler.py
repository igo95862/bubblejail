#!/usr/bin/python3 -IO
# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2023 igo95862

# This file is part of bubblejail.
# bubblejail is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# bubblejail is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with bubblejail.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

from argparse import ArgumentParser
from compileall import compile_dir
from pathlib import Path
from shutil import copy


def compiler(build_dir: Path, prefix: Path, optimize_level: int) -> None:
    compile_dir(
        dir=str(build_dir),
        optimize=0,
        workers=0,
        ddir=str(prefix),
    )

    if optimize_level > 0:
        compile_dir(
            dir=str(build_dir),
            optimize=optimize_level,
            workers=0,
            ddir=str(prefix),
        )


def copy_files(source_files: list[Path], output_dir: Path) -> None:
    for x in source_files:
        copy(x, output_dir)


def compiler_main() -> None:
    parser = ArgumentParser()

    parser.add_argument(
        '--input-files',
        action='store',
        required=True,
        type=Path,
        nargs='*',
    )
    parser.add_argument(
        '--output-dir',
        action='store',
        required=True,
        type=Path,
    )

    parser.add_argument(
        '--lib-prefix',
        action='store',
        required=True,
        type=Path,
    )
    parser.add_argument(
        '--optimize-level',
        type=int,
        default=1,
    )

    args = parser.parse_args()
    copy_files(args.input_files, args.output_dir)
    compiler(
        args.output_dir,
        args.lib_prefix,
        args.optimize_level,
    )


if __name__ == "__main__":
    compiler_main()

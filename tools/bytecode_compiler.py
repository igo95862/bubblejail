#!/usr/bin/python3 -B
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
from __future__ import annotations

import sys
from argparse import ArgumentParser
from os import environ
from compileall import compile_dir
from pathlib import Path


def compiler(optimize_level: int, packages_dir: Path) -> None:
    # Always compile bytecode to __pycache__ folder
    sys.pycache_prefix = None

    install_dir = Path(environ["MESON_INSTALL_DESTDIR_PREFIX"])
    install_prefix = Path(environ["MESON_INSTALL_PREFIX"])
    is_dry_run = "MESON_INSTALL_DRY_RUN" in environ

    if install_dir == install_prefix:
        print("Not compiling bytecode when installing on root")
        return

    if packages_dir.is_absolute():
        destdir = install_dir.parents[len(install_prefix.parents)-1]
        python_packages_dir = destdir / packages_dir.relative_to("/")
        python_packages_prefix = packages_dir
    else:
        python_packages_dir = install_dir / packages_dir
        python_packages_prefix = install_prefix / packages_dir

    if is_dry_run:
        print("Would call compile_dir with:")
        print("dir:", python_packages_dir)
        print("ddir:", python_packages_prefix)
        return

    compile_dir(
        dir=str(python_packages_dir),
        optimize=0,
        workers=0,
        ddir=str(python_packages_prefix),
    )

    if optimize_level > 0:
        compile_dir(
            dir=str(python_packages_dir),
            optimize=optimize_level,
            workers=0,
            ddir=str(python_packages_prefix),
        )


def compiler_main() -> None:
    parser = ArgumentParser()

    parser.add_argument(
        "--optimize-level",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--packages-dir",
        required=True,
        type=Path,
    )

    compiler(**vars(parser.parse_args()))


if __name__ == "__main__":
    compiler_main()

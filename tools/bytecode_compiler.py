#!/usr/bin/python3 -IOO

from argparse import ArgumentParser
from compileall import compile_dir
from pathlib import Path
from pprint import pp
from shutil import copy
from sys import argv
from typing import List


def compiler(build_dir: Path, prefix: Path) -> None:
    compile_dir(
        dir=str(build_dir),
        optimize=0,
        workers=0,
        ddir=str(prefix),
    )

    compile_dir(
        dir=str(build_dir),
        optimize=2,
        workers=0,
        ddir=str(prefix),
    )


def copy_files(source_files: List[Path], output_dir: Path) -> None:
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

    names = parser.parse_args()
    pp(names)
    copy_files(names.input_files, names.output_dir)
    compiler(names.output_dir, names.lib_prefix)


if __name__ == "__main__":
    pp(argv)
    compiler_main()

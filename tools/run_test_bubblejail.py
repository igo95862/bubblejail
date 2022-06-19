#!/usr/bin/env python3
from os import environ
from pathlib import Path
from shlex import split as shelx_split
from traceback import print_exc
from typing import Generator

from bubblejail.bubblejail_cli import bubblejail_main
from bubblejail.bubblejail_directories import BubblejailDirectories


def shell_main() -> None:
    build_dir = Path(environ['MESON_BUILD_ROOT'])
    custom_data_dir = build_dir / 'bubblejail_test_datadir'
    custom_data_dir.mkdir(exist_ok=True)

    def custom_datadirs() -> Generator[Path, None, None]:
        yield custom_data_dir

    setattr(
        BubblejailDirectories,
        'iter_bubblejail_data_directories',
        custom_datadirs,
    )

    while True:
        try:
            input_line = input('bubblejail>> ')
        except EOFError:
            print()
            return

        args = shelx_split(input_line)

        try:
            bubblejail_main(args)
        except Exception:
            print_exc()


if __name__ == '__main__':
    shell_main()

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from os import environ
from pathlib import Path
from readline import read_history_file, set_history_length, write_history_file
from shlex import split as shelx_split
from traceback import print_exc
from typing import Any, Generator

from bubblejail.bubblejail_cli import bubblejail_main
from bubblejail.bubblejail_directories import BubblejailDirectories
from bubblejail.bubblejail_gui_qt import run_gui
from bubblejail.bubblejail_instance import BubblejailInstance


def setup_test_env() -> None:
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

    def disable_desktop_entry(*args: Any, **kwargs: Any) -> None:
        ...

    setattr(
        BubblejailDirectories,
        'overwrite_desktop_entry_for_profile',
        disable_desktop_entry,
    )

    helper_path = build_dir / 'src/bubblejail/bubblejail_helper.py'
    original_run = BubblejailInstance.async_run_init

    async def run_with_helper_script(
        self: BubblejailInstance,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        kwargs["debug_helper_script"] = helper_path
        await original_run(
            self,
            *args,
            **kwargs,
        )

    setattr(
        BubblejailInstance,
        'async_run_init',
        run_with_helper_script,
    )


def shell_main() -> None:
    build_dir = Path(environ['MESON_BUILD_ROOT'])
    history_file = build_dir / 'bubblejail_cmd_history'
    history_file.touch(exist_ok=True)
    read_history_file(history_file)
    set_history_length(1000)

    while True:
        try:
            input_line = input('bubblejail>> ')
        except EOFError:
            print()
            return
        finally:
            write_history_file(history_file)

        args = shelx_split(input_line)

        try:
            bubblejail_main(args)
        except Exception:
            print_exc()
        except SystemExit:
            ...


def gui_main() -> None:
    run_gui()


TEST_RUNNERS = {
    'shell': shell_main,
    'gui': gui_main,
}


def main() -> None:
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        'runner',
        choices=TEST_RUNNERS.keys(),
    )
    args = arg_parser.parse_args()
    setup_test_env()
    TEST_RUNNERS[args.runner]()


if __name__ == '__main__':
    main()

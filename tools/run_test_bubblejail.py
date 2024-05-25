#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from readline import read_history_file, set_history_length, write_history_file
from shlex import split as shelx_split
from traceback import print_exc
from typing import Any, Generator

from bubblejail.bubblejail_cli import bubblejail_main
from bubblejail.bubblejail_directories import BubblejailDirectories
from bubblejail.bubblejail_gui_qt import run_gui
from bubblejail.bubblejail_instance import BubblejailInstance


# How to run testing bubblejail
# 1. Create venv:
#    python -m venv --system-site-packages venv
#
# 2. Use meson-python editable installs:
#     ./venv/bin/pip install \
#       --no-build-isolation --config-settings=editable-verbose=true \
#       --config-settings=setup-args=-Dman=false \
#       --config-settings=setup-args=-Duse-vendored-python-lxns=enabled \
#       --config-settings=install-args=--tags=runtime \
#       --config-settings=setup-args=-Dallow-site-packages-dir=true \
#       --editable .
#
# 3. Run this script with venv:
#    ./venv/bin/python ./tools/run_test_bubblejail.py shell

PROJECT_ROOT_PATH = Path(__file__).parent.parent
BUILD_DIR = PROJECT_ROOT_PATH / "build"


def setup_test_env() -> None:
    custom_data_dir = BUILD_DIR / 'bubblejail_test_datadir'
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

    helper_path = PROJECT_ROOT_PATH / 'src/bubblejail/bubblejail_helper.py'
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

    import bubblejail.bubblejail_instance

    custom_run_dir = BUILD_DIR / "bubblejail_test_rundir"
    custom_run_dir.mkdir(exist_ok=True)

    def custom_runtime_dir() -> str:
        return str(custom_run_dir)

    setattr(
        bubblejail.bubblejail_instance,
        "get_runtime_dir",
        custom_runtime_dir,
    )


def shell_main() -> None:
    history_file = BUILD_DIR / 'bubblejail_cmd_history'
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

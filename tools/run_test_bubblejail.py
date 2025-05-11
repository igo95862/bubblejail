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
from typing import Any

# How to run testing bubblejail
# 1. Create venv using provided helper script:
#       python -m tools.venv_setup
# 2. Run this script with venv.
#   To run CLI:
#       ./venv/bin/python ./tools/run_test_bubblejail.py shell
#   To run GUI:
#       ./venv/bin/python ./tools/run_test_bubblejail.py gui

PROJECT_ROOT_PATH = Path(__file__).parent.parent
BUILD_DIR = PROJECT_ROOT_PATH / "build"
TEST_DIR = BUILD_DIR / "bubblejail_test"


def setup_test_env() -> None:
    TEST_DIR.mkdir(exist_ok=True)

    test_data_dir = TEST_DIR / "data"
    test_data_dir.mkdir(exist_ok=True)
    environ["XDG_DATA_HOME"] = str(test_data_dir)

    test_config_dir = TEST_DIR / "config"
    test_config_dir.mkdir(exist_ok=True)
    environ["XDG_CONFIG_HOME"] = str(test_config_dir)


def setup_mocks() -> None:
    from bubblejail.bubblejail_instance import BubblejailInstance

    helper_path = PROJECT_ROOT_PATH / "src/bubblejail/bubblejail_helper.py"
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
        "async_run_init",
        run_with_helper_script,
    )

    runtime_dir_path = TEST_DIR / "run"
    runtime_dir_path.mkdir(exist_ok=True)

    def runtime_dir(self: BubblejailInstance) -> Path:
        return runtime_dir_path / f"bubblejail/{self.name}"

    setattr(
        BubblejailInstance,
        "runtime_dir",
        property(fget=runtime_dir),
    )


def shell_main() -> None:
    history_file = BUILD_DIR / "bubblejail_cmd_history"
    history_file.touch(exist_ok=True)
    read_history_file(history_file)
    set_history_length(1000)

    setup_mocks()

    from bubblejail.bubblejail_cli import bubblejail_main

    while True:
        try:
            input_line = input("bubblejail>> ")
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
    setup_mocks()

    from bubblejail.bubblejail_gui_qt import run_gui

    run_gui()


TEST_RUNNERS = {
    "shell": shell_main,
    "gui": gui_main,
}


def main() -> None:
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "runner",
        choices=TEST_RUNNERS.keys(),
    )
    args = arg_parser.parse_args()
    setup_test_env()
    TEST_RUNNERS[args.runner]()


if __name__ == "__main__":
    main()

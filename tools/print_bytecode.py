#!/usr/bin/python3 -B
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from marshal import loads as marshal_loads
from pathlib import Path


def print_bytecode(bytecode_path: Path) -> None:
    with open(bytecode_path, mode="rb") as f:
        bytecode_contents = f.read()

    print(marshal_loads(bytecode_contents[16:]))


def main() -> None:
    arg_parser = ArgumentParser()
    arg_parser.add_argument("bytecode_path", type=Path)

    print_bytecode(**vars(arg_parser.parse_args()))


if __name__ == "__main__":
    main()

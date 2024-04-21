#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from json import load as json_load
from typing import Any

from jinja2 import Environment, FileSystemLoader


def convert_constant_name(constant_name: str) -> str:
    if constant_name.startswith('__NR'):
        return constant_name.replace('__NR', 'syscall').upper()

    return constant_name


def get_constant_type(constant: Any) -> str:
    match constant:
        case int():
            return 'int'
        case _:
            raise TypeError(f"Unknown type: {repr(constant)}")


def generate_constants_file(
    template_dir: Path,
    constants_json_file: Path,
) -> None:

    with open(constants_json_file) as f:
        constants_dict: dict[str, str | int] = json_load(f)

    constants_dict.pop('')
    env = Environment(
        loader=FileSystemLoader(template_dir),
    )
    env.filters['convert_constant_name'] = convert_constant_name

    template = env.get_template("namespaces_constants.py.jinja2")
    print(template.render(
        constants_data=constants_dict,
        type=get_constant_type,
    ))


def main() -> None:
    arg_parse = ArgumentParser()
    arg_parse.add_argument(
        '--template-dir',
        required=True,
        type=Path,
    )
    arg_parse.add_argument(
        'constants_json_file',
        type=Path,
    )

    generate_constants_file(**vars(arg_parse.parse_args()))


if __name__ == "__main__":
    main()

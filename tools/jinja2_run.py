#!/usr/bin/python3 -B
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from sys import stdout

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def execute_template(
    define: list[tuple[str, str]],
    template_dir: Path,
    template_name: str,
) -> None:
    define_dict = {x[0]: x[1] for x in define}

    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    template = env.get_template(template_name)
    stdout.write(template.render(**define_dict))


def main() -> None:
    arg_parse = ArgumentParser()
    arg_parse.add_argument(
        "--define",
        action="append",
        nargs=2,
        default=[],
    )
    arg_parse.add_argument(
        "--template-dir",
        required=True,
        type=Path,
    )
    arg_parse.add_argument(
        "template_name",
    )

    execute_template(**vars(arg_parse.parse_args()))


if __name__ == "__main__":
    main()

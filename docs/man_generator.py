#!/usr/bin/python3 -O
# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 023 igo95862

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
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from bubblejail.bubblejail_cli import BUBBLEJAIL_CMD

if TYPE_CHECKING:
    from collections.abc import Iterator


SUBCOMMAND_HELP = {
    'run': """The arguments are optional if you have
_executable_name_ key set in config.

Otherwise, you *must* specify arguments to run.

The arguments *must* include the program executable. Example:

\tbubblejail run FirefoxInstance firefox google.com

If the instance already running this command will run the arguments inside
the sandbox. If _--wait_ option is passed the output of the command
will be returned.
""",
    'create': """When a new instance is created a desktop
entry will be also created.

Creating an instance from profile will print some import tips that you
can use to import configuration from unsandboxed application.
""",
    'generate-desktop-entry': """Desktop entry can either be specified
by profile, path, name or extracted from metadata when instance was created.
""",
    'edit': """After exiting the editor, the file is validated and
only written if validation is successful.

_EDITOR_ environmental variable must be set.
""",
    'list': '\n'.join(
        f"- *{x}*" for x in
        BUBBLEJAIL_CMD['list']['add_argument']['list_what']['choices']
    )
}

OPTION_HELP = {
    'run': {
        '--debug-bwrap-args': """The instance name must be separated with
extra -- from the instance name.

This option can be repeated multiple times for multiple args to bwrap.

Example with adding capability and running as UID and GID
0 for test_instance instance:

\tbubblejail run --debug-bwrap-args cap-add CAP_SYS_ADMIN
\t\\--debug-bwrap-args uid 0 --debug-bwrap-args gid 0 -- test_instance

"""
    },
    'create': {
        '--profile': """If omitted an empty profile will be used and
the user will have to define the configuration manually.

There is also a _generic_ profile which has some common settings such
as network and windowing system access.
"""
    },
}


def format_option(subcommand: str, option: str) -> Iterator[str]:
    option_data = BUBBLEJAIL_CMD[subcommand]['add_argument'][option]

    yield f"*{option}*"

    option_action = option_data.get('action')
    match option_action:
        case 'store_true' | 'store_false':
            return

    option_metavar = option_data.get('metavar')
    match option_metavar:
        case str():
            yield f"<{option_metavar}>"
        case tuple():
            yield from (f"<{x}>" for x in option_metavar)
        case None:
            ...
        case _:
            raise TypeError


def get_option_description(subcommand: str, option: str) -> str:
    option_data = BUBBLEJAIL_CMD[subcommand]['add_argument'][option]
    option_help = option_data['help']
    try:
        option_extra_description = OPTION_HELP[subcommand][option]
    except KeyError:
        option_extra_description = ''

    option_text = '\n\n'.join(
        (
            option_help,
            option_extra_description,
        )
    )

    return indent(option_text, '\t')


def get_options(subcommand: str) -> tuple[str, ...]:
    return tuple(
        filter(
            lambda x: x.startswith('-'),
            BUBBLEJAIL_CMD[subcommand]['add_argument'].keys(),
        )
    )


def format_arg_names(subcommand: str) -> Iterator[str]:
    if get_options(subcommand):
        yield '[options...]'

    add_arguments_dict = BUBBLEJAIL_CMD[subcommand]['add_argument']
    for add_argument, options in add_arguments_dict.items():
        if add_argument.startswith('-'):
            continue

        if options.get('nargs'):
            yield f"[{add_argument}...]"
        else:
            yield f"[{add_argument}]"


def get_subcommand_description(subcommand: str) -> str:
    return '\n\n'.join(
        (
            BUBBLEJAIL_CMD[subcommand]['description'],
            SUBCOMMAND_HELP.get(subcommand, ''),
        )
    )


def generate_cmd_man(template_dir: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(template_dir),
        undefined=StrictUndefined,
    )

    template = env.get_template('bubblejail.1.scd.jinja2')

    print(
        template.render(
            subcommands=BUBBLEJAIL_CMD.keys(),
            get_subcommand_description=get_subcommand_description,
            get_options=get_options,
            format_arg_names=format_arg_names,
            get_option_description=get_option_description,
            format_option=format_option,
        )
    )


def main() -> None:
    arg_parse = ArgumentParser()
    arg_parse.add_argument(
        '--template-dir',
        required=True,
        type=Path,
    )
    args = arg_parse.parse_args()

    generate_cmd_man(**vars(args))


if __name__ == "__main__":
    main()

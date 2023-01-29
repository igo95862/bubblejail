# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019-2023 igo95862

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

from argparse import REMAINDER as ARG_REMAINDER
from argparse import ArgumentParser
from asyncio import run as async_run
from pathlib import Path
from sys import argv
from typing import TYPE_CHECKING

from .bubblejail_directories import BubblejailDirectories
from .bubblejail_utils import BubblejailSettings
from .services import SERVICES_CLASSES

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Iterator
    from typing import Any, Optional, TypedDict


def iter_profile_names() -> Generator[str, None, None]:
    for profiles_directory in BubblejailDirectories.\
            iter_profile_directories():

        for profile_file in profiles_directory.iterdir():
            yield profile_file.stem


def iter_instance_names() -> Generator[str, None, None]:
    for instance_directory in BubblejailDirectories.iter_instances_path():
        yield instance_directory.name


def iter_subcommands() -> Generator[str, None, None]:
    yield from BUBBLEJAIL_CMD.keys()


def iter_subcommand_options(
        subcommand_text: str,
) -> Generator[str, None, None]:
    yield from (
        x
        for x in
        BUBBLEJAIL_CMD[subcommand_text]['add_argument']
        if x.startswith('--')
    )


def iter_list_choices() -> Iterable[str]:
    choices = BUBBLEJAIL_CMD['list']['add_argument']['list_what']['choices']
    assert isinstance(choices, set)
    return choices


def _extra_args_converter(command_sequence: list[str]
                          ) -> Generator[str, None, None]:
    command_iter = iter(command_sequence)

    try:
        argword = next(command_iter)
    except StopIteration:
        raise ValueError('Expected at least one argument')

    yield f"--{argword}"

    yield from command_iter


def run_bjail(instance_name: str,
              args_to_instance: list[str],
              wait: bool, dry_run: bool, debug_bwrap_args: list[list[str]],
              debug_shell: bool, debug_log_dbus: bool,
              debug_helper_script: Optional[Path]) -> None:
    try:
        instance = BubblejailDirectories.instance_get(instance_name)

        if instance.is_running():
            if dry_run:
                print('Found helper socket.')
                print('Args to be sent: ', args_to_instance)
                return

            command_return_text = async_run(
                instance.send_run_rpc(
                    args_to_run=args_to_instance,
                    wait_for_response=wait,
                )
            )
            if wait:
                print(command_return_text)
        else:
            extra_bwrap_args: Optional[list[str]]
            if debug_bwrap_args is not None:
                extra_bwrap_args = []
                for x in debug_bwrap_args:
                    extra_bwrap_args.extend(_extra_args_converter(x))
            else:
                extra_bwrap_args = None

            async_run(
                instance.async_run_init(
                    args_to_run=args_to_instance,
                    debug_shell=debug_shell,
                    debug_helper_script=debug_helper_script,
                    debug_log_dbus=debug_log_dbus,
                    dry_run=dry_run,
                    extra_bwrap_args=extra_bwrap_args,
                )
            )
    except Exception:
        from os import isatty
        from sys import stderr

        if not isatty(stderr.fileno()):
            from subprocess import run as subprocess_run
            from traceback import format_exc

            try:
                subprocess_run(
                    (
                        'notify-send',
                        '--urgency', 'critical',
                        '--icon', 'bubblejail-config',
                        f"Failed to run instance: {instance_name}",
                        f"Exception: {format_exc(0)}"
                    )
                )
            except FileNotFoundError:
                # Make notify-send optional
                ...
        raise


def bjail_list(list_what: str) -> None:
    str_iterator: Iterator[str]

    if list_what == 'instances':
        str_iterator = iter_instance_names()
    elif list_what == 'profiles':
        str_iterator = iter_profile_names()
    elif list_what == 'services':
        str_iterator = (x.name for x in SERVICES_CLASSES)
    elif list_what == 'subcommands':
        str_iterator = iter_subcommands()

    for string in str_iterator:
        print(string)


def bjail_create(new_instance_name: str,
                 profile: Optional[str],
                 no_desktop_entry: bool) -> None:
    BubblejailDirectories.create_new_instance(
        new_name=new_instance_name,
        profile_name=profile,
        create_dot_desktop=no_desktop_entry,
        print_import_tips=True,
    )


def bjail_edit(instance_name: str) -> None:
    instance = BubblejailDirectories.instance_get(instance_name)
    async_run(instance.edit_config_in_editor())


def bjail_create_desktop_entry(instance_name: str,
                               profile: Optional[str],
                               desktop_entry: Optional[str]) -> None:
    BubblejailDirectories.overwrite_desktop_entry_for_profile(
        instance_name=instance_name,
        profile_name=profile,
        desktop_entry_name=desktop_entry,
    )


if TYPE_CHECKING:
    class CmdMetaDataDict(TypedDict):
        add_argument: dict[str, dict[str, Any]]
        argument: str
        func: Callable[..., None]

BUBBLEJAIL_CMD: dict[str, CmdMetaDataDict] = {
    'run': {
        'add_argument': {
            '--debug-shell': {
                'action': 'store_true',
                'help': (
                    'Opens a shell inside the sandbox instead of '
                    'running program. Useful for debugging.'
                ),
            },
            '--dry-run': {
                'action': 'store_true',
                'help': (
                    'Prints the bwrap and xdg-desktop-entry arguments '
                    'instead of running.'
                ),
            },
            '--debug-helper-script': {
                'type': Path,
                'help': (
                    'Use the specified helper script. '
                    'This is mainly development command.'
                ),
            },
            '--debug-log-dbus': {
                'action': 'store_true',
                'help': 'Enables D-Bus proxy logging.',
            },
            '--wait': {
                'action': 'store_true',
                'help': (
                    'Wait on the command inserted in to sandbox '
                    'and get the output.'
                ),
            },
            '--debug-bwrap-args': {
                'action': 'append',
                'nargs': '+',
                'help': (
                    'Add extra option to bwrap. '
                    'First argument will be prefixed with `--`.'
                ),
            },
            'instance_name': {
                'help': 'Instance to run.',
            },
            'args_to_instance': {
                'nargs': ARG_REMAINDER,
                'help': 'Command and its arguments to run inside instance.',
            },
        },
        'argument': 'instance',
        'func': run_bjail,
        'description': 'Launch instance or run command inside.',
    },
    'create': {
        'add_argument': {
            '--profile': {
                'help': 'Bubblejail profile to use.',
            },
            '--no-desktop-entry': {
                'action': 'store_false',
                'help': 'Do not create desktop entry.',
            },
            'new_instance_name': {
                'help': 'New instance name.',
            },
        },
        'argument': 'any',
        'func': bjail_create,
        'description': 'Create new bubblejail instance.',
    },
    'list': {
        'add_argument': {
            'list_what': {
                'choices': {
                    'instances',
                    'profiles',
                    'services',
                },
                'default': 'instances',
                'help': 'Type of entity to list.',
            },
        },
        'argument': 'any',
        'func': bjail_list,
        'description': 'List certain bubblejail entities.',
    },
    'edit': {
        'add_argument': {
            'instance_name': {
                'help': 'Instance to edit config.',
            },
        },
        'argument': 'instance',
        'func': bjail_edit,
        'description': 'Open instance config in $EDITOR.',
    },
    'generate-desktop-entry': {
        'add_argument': {
            '--profile': {
                'help': 'Use desktop entry specified in profile.',
            },
            '--desktop-entry': {
                'help': 'Desktop entry name or path to use.',
            },
            'instance_name': {
                'help': 'Instance to generate desktop entry for',
            },
        },
        'argument': 'instance',
        'func': bjail_create_desktop_entry,
        'description': 'Generate XDG desktop entry for an instance.',
    },
}


def create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            'Bubblejail is a bubblewrap based sandboxing utility.'
        )
    )
    subparsers = parser.add_subparsers(
        required=True,
        description='Available subcommands.'
    )
    for subcommand_name, subcommand_data in BUBBLEJAIL_CMD.items():
        subfunction = subcommand_data.pop('func')
        subcommand_data.pop('argument')
        subcommand_add_argument = subcommand_data.pop('add_argument')
        subparser = subparsers.add_parser(
            subcommand_name,
            **subcommand_data,
        )
        subparser.set_defaults(
            func=subfunction,
        )
        for arg_name, arg_options in subcommand_add_argument.items():
            subparser.add_argument(
                arg_name,
                **arg_options,
            )

    return parser


def bubblejail_main(arg_list: Optional[list[str]] = None) -> None:
    # Short circuit to auto-complete
    if argv[1] == 'auto-complete':
        from .bubblejail_cli_autocomplete import run_autocomplete
        run_autocomplete()
        return

    parser = create_arg_parser()
    parser.add_argument(
        '--version',
        action='version',
        version=BubblejailSettings.VERSION,
    )

    args_dict = vars(parser.parse_args(arg_list))

    func = args_dict.pop('func')

    func(**args_dict)

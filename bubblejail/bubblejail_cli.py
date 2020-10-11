# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019, 2020 igo95862

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


from argparse import REMAINDER as ARG_REMAINDER
from argparse import ArgumentParser, Namespace
from asyncio import run as async_run
from pathlib import Path
from shlex import split as shlex_split
from typing import Generator, Iterator, List, Iterable, Dict, Set, Optional

from .bubblejail_directories import BubblejailDirectories
from .services import SERVICES_CLASSES


class CommandMetadata:
    cmd_map: Dict[str, Set[str]] = {}
    current_command: Optional[str] = None
    cmd_want_instance: Set[str] = set()

    cmd_list_options = {'instances', 'profiles', 'services',
                        '_auto_complete', }

    @classmethod
    def add_subcommand(cls, command: str) -> str:
        cls.cmd_map[command] = set()
        cls.current_command = command
        return command

    @classmethod
    def instance_arg(cls) -> str:
        if cls.current_command is not None:
            cls.cmd_want_instance.add(cls.current_command)
            return 'instance_name'
        else:
            raise RuntimeError('Expected current command got None')

    @classmethod
    def add_option(cls, option: str) -> str:
        if cls.current_command is not None:
            cls.cmd_map[cls.current_command].add(option)
            return option
        else:
            raise RuntimeError('Expected current command got None')


def run_bjail(args: Namespace) -> None:
    instance_name = args.instance_name

    instance = BubblejailDirectories.instance_get(instance_name)

    if instance.is_running():
        if args.dry_run:
            print('Found helper socket.')
            print('Args to be sent: ', args.args_to_instance)
            return

        command_return_text = async_run(
            instance.send_run_rpc(
                args_to_run=args.args_to_instance,
                wait_for_response=args.wait,
            )
        )
        if args.wait:
            print(command_return_text)
    else:
        async_run(
            instance.async_run_init(
                args_to_run=args.args_to_instance,
                debug_shell=args.debug_shell,
                debug_helper_script=args.debug_helper_script,
                debug_log_dbus=args.debug_log_dbus,
                dry_run=args.dry_run,
            )
        )


def iter_profile_names() -> Generator[str, None, None]:
    for profiles_directory in BubblejailDirectories.\
            iter_profile_directories():

        for profile_file in profiles_directory.iterdir():
            yield profile_file.stem


def iter_instance_names() -> Generator[str, None, None]:
    for instance_directory in BubblejailDirectories.iter_instances_path():
        yield instance_directory.name


def iter_subcommands() -> Generator[str, None, None]:
    yield from CommandMetadata.cmd_map.keys()


def iter_subcommand_options(
        subcommand_text: str) -> Generator[str, None, None]:
    yield from CommandMetadata.cmd_map[subcommand_text]


class AutoCompleteParser:
    def __init__(self,
                 args: Namespace,
                 words: List[str]
                 ):
        self.args = args
        self.words = words
        self.subcommands = CommandMetadata.cmd_map.keys()
        self.auto_complete_iterable: Iterable[str] = self.subcommands

    def auto_complete_parser(
            self,
    ) -> None:

        want_instance_set = {'edit', 'run', 'generate-desktop-entry'}
        base_options = {'--help'}

        # enumerate words to allow LL parser lookahead
        enumer_words = enumerate(self.words)
        _ = next(enumer_words)  # cycle 'bubblejail'
        # 1. Parse base options (--help) and subcommands
        while True:
            index, token = next(enumer_words)
            # If its an option autocomplete to base options
            if token.startswith('-'):
                self.auto_complete_iterable = base_options
                continue
            else:
                # else it is probably a subcommand
                subcommand = token
                break

        if subcommand not in self.subcommands:
            # If subcommand is not recognized
            # do not try to auto complete

            try:
                self.words[index+1]
            except IndexError:
                ...
            else:
                self.auto_complete_iterable = []
            return

        subcommand_options = CommandMetadata.cmd_map[subcommand]

        subject_set = False

        while True:
            index, token = next(enumer_words)

            if subject_set:
                # if we set our subject (i.e. instance)
                # extra arguments should not be completed
                self.auto_complete_iterable = []
                return

            if token.startswith('-'):
                # Parse base options and subcommands
                self.auto_complete_iterable = subcommand_options
                continue

            if subcommand == 'list':
                self.auto_complete_iterable = CommandMetadata.cmd_list_options
                subject_set = True
                continue

            if self.words[index - 1] == '--profile':
                # Wants profile
                self.auto_complete_iterable = iter_profile_names()
                continue

            if subcommand in want_instance_set:
                # Wants instance name
                self.auto_complete_iterable = iter_instance_names()
                subject_set = True
                continue

            # Does not want anything
            self.auto_complete_iterable = []

    def auto_complete(self) -> Generator[str, None, None]:
        try:
            self.auto_complete_parser()
        except StopIteration:
            ...

        yield from self.auto_complete_iterable


def bjail_list(args: Namespace) -> None:
    str_iterator: Iterator[str]

    if args.list_what == 'instances':
        str_iterator = iter_instance_names()
    elif args.list_what == 'profiles':
        str_iterator = iter_profile_names()
    elif args.list_what == 'services':
        str_iterator = (x.name for x in SERVICES_CLASSES)
    elif args.list_what == 'subcommands':
        str_iterator = iter_subcommands()
    elif args.list_what == '_auto_complete':
        command_line = args.command_line

        words = shlex_split(command_line)

        if command_line[-1].isspace():
            words.append('')

        a = AutoCompleteParser(args, words)
        str_iterator = a.auto_complete()

    for string in str_iterator:
        print(string)


def bjail_create(args: Namespace) -> None:
    BubblejailDirectories.create_new_instance(
        new_name=args.new_instance_name,
        profile_name=args.profile,
        create_dot_desktop=args.no_desktop_entry,
        print_import_tips=True,
    )


def bjail_edit(args: Namespace) -> None:
    instance = BubblejailDirectories.instance_get(args.instance_name)
    async_run(instance.edit_config_in_editor())


def bjail_create_desktop_entry(args: Namespace) -> None:
    BubblejailDirectories.overwrite_desktop_entry_for_profile(
        instance_name=args.instance_name,
        profile_name=args.profile,
        desktop_entry_name=args.desktop_entry,
    )


def bubblejail_main() -> None:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(
        required=True,
    )
    # run subcommand
    parser_run = subparsers.add_parser(
        CommandMetadata.add_subcommand('run')
    )

    parser_run.add_argument(
        CommandMetadata.add_option('--debug-shell'), action='store_true')
    parser_run.add_argument(
        CommandMetadata.add_option('--dry-run'), action='store_true')
    parser_run.add_argument(
        CommandMetadata.add_option('--debug-helper-script'), type=Path)
    parser_run.add_argument(
        CommandMetadata.add_option('--debug-log-dbus'), action='store_true')
    parser_run.add_argument(
        CommandMetadata.add_option('--wait'), action='store_true')

    parser_run.add_argument(CommandMetadata.instance_arg())
    parser_run.add_argument(
        'args_to_instance',
        nargs=ARG_REMAINDER,
    )
    parser_run.set_defaults(func=run_bjail)
    # create subcommand
    parser_create = subparsers.add_parser(
        CommandMetadata.add_subcommand('create')
    )
    parser_create.set_defaults(func=bjail_create)
    parser_create.add_argument(
        CommandMetadata.add_option('--profile'),
    )

    parser_create.add_argument(
        CommandMetadata.add_option('--no-desktop-entry'),
        action='store_false',
    )
    parser_create.add_argument('new_instance_name')
    # list subcommand
    parser_list = subparsers.add_parser(
        CommandMetadata.add_subcommand('list')
    )
    parser_list.add_argument(
        '--command-line',
    )
    parser_list.add_argument(
        'list_what',
        choices=CommandMetadata.cmd_list_options,
        default='instances',
    )

    parser_list.set_defaults(
        func=bjail_list,
        parser=parser,
    )

    # Edit subcommand
    parser_edit = subparsers.add_parser(
        CommandMetadata.add_subcommand('edit')
    )
    parser_edit.add_argument(CommandMetadata.instance_arg())
    parser_edit.set_defaults(func=bjail_edit)

    # Generate desktop entry subcommand
    parser_desktop_entry = subparsers.add_parser(
        CommandMetadata.add_subcommand('generate-desktop-entry')
    )
    parser_desktop_entry.add_argument(
        CommandMetadata.add_option('--profile'),
    )
    parser_desktop_entry.add_argument(
        CommandMetadata.add_option('--desktop-entry'),
    )
    parser_desktop_entry.add_argument(CommandMetadata.instance_arg())
    parser_desktop_entry.set_defaults(func=bjail_create_desktop_entry)

    args = parser.parse_args()

    args.func(args)

# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019 igo95862

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
from typing import Iterator

from .bubblejail_instance import BubblejailInstance, get_data_directory
from .profiles import PROFILES


def iter_instance_names() -> Iterator[str]:
    data_dir = get_data_directory()
    for x in data_dir.iterdir():
        if x.is_dir():
            yield str(x.stem)


def run_bjail(args: Namespace) -> None:
    instance_name = args.instance_name

    async_run(
        BubblejailInstance(
            instance_name
        ).async_run(
            args_to_run=args.args_to_instance,
            debug_print_args=args.debug_print_args,
            debug_shell=args.debug_shell,
            dry_run=args.dry_run,
        ))


def bjail_list(args: Namespace) -> None:
    if args.list_what == 'instances':
        for x in iter_instance_names():
            print(x)
    elif args.list_what == 'profiles':
        for x in PROFILES:
            print(x)


def bjail_create(args: Namespace) -> None:
    profile = PROFILES[args.profile]
    new_instance = BubblejailInstance.create_new(
        new_name=args.new_instance_name,
        profile_name=args.profile,
    )
    new_instance.generate_dot_desktop(str(profile.dot_desktop_path))


def main() -> None:
    parser = ArgumentParser()
    subparcers = parser.add_subparsers()
    # run subcommand
    parser_run = subparcers.add_parser('run')
    if __debug__:
        parser_run.add_argument('--debug-print-args', action='store_true')
        parser_run.add_argument('--debug-shell', action='store_true')
        parser_run.add_argument('--dry-run', action='store_true')

    parser_run.add_argument('instance_name')
    parser_run.add_argument(
        'args_to_instance',
        nargs=ARG_REMAINDER,
    )
    parser_run.set_defaults(func=run_bjail)
    # create subcommand
    parser_create = subparcers.add_parser('create')
    parser_create.set_defaults(func=bjail_create)
    parser_create.add_argument(
        '--profile',
        choices=PROFILES.keys(),
        required=True,
    )
    parser_create.add_argument('new_instance_name')
    # list subcommand
    parser_list = subparcers.add_parser('list')
    parser_list.add_argument(
        'list_what',
        choices=('instances', 'profiles'),
        default='instances',)
    parser_list.set_defaults(func=bjail_list)

    args = parser.parse_args()
    args.func(args)

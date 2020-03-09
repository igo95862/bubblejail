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
from typing import Iterator

from pkg_resources import resource_filename
from toml import load as toml_load

from .bubblejail_instance import BubblejailInstance
from .bubblejail_utils import BubblejailProfile


def iter_instance_names() -> Iterator[str]:
    data_dir = BubblejailInstance.DATA_INSTANCE_DIR
    for x in data_dir.iterdir():
        if x.is_dir():
            yield str(x.stem)


def run_bjail(args: Namespace) -> None:
    instance_name = args.instance_name

    async_run_kwargs = {
        'args_to_run': args.args_to_instance,
    }

    if __debug__:
        async_run_kwargs['debug_shell'] = args.debug_shell
        async_run_kwargs['dry_run'] = args.dry_run
        async_run_kwargs['debug_helper_script'] = args.debug_helper_script
        async_run_kwargs['debug_log_dbus'] = args.debug_log_dbus

    async_run(
        BubblejailInstance(
            instance_name
        ).async_run(**async_run_kwargs)
    )


def bjail_list(args: Namespace) -> None:
    if args.list_what == 'instances':
        for x in iter_instance_names():
            print(x)
    elif args.list_what == 'profiles':
        profiles_dir = Path(resource_filename(__name__, 'profiles'))
        for profile_file in profiles_dir.iterdir():
            print(profile_file.stem)


def load_profile(profile_name: str) -> BubblejailProfile:
    profiles_dir = Path(resource_filename(__name__, 'profiles'))
    with open(profiles_dir / f"{profile_name}.toml") as f:
        return BubblejailProfile(**toml_load(f))


def bjail_create(args: Namespace) -> None:
    if args.profile is None:
        profile = BubblejailProfile()
    else:
        profile = load_profile(args.profile)
    BubblejailInstance.create_new(
        new_name=args.new_instance_name,
        profile=profile,
        create_dot_desktop=args.no_desktop_entry,
    )


def bubblejail_main() -> None:
    parser = ArgumentParser()
    subparcers = parser.add_subparsers(
        required=True,
    )
    # run subcommand
    parser_run = subparcers.add_parser('run')
    if __debug__:
        parser_run.add_argument('--debug-shell', action='store_true')
        parser_run.add_argument('--dry-run', action='store_true')
        parser_run.add_argument('--debug-helper-script', type=Path)
        parser_run.add_argument('--debug-log-dbus', action='store_true')

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
    )
    parser_create.add_argument(
        '--no-desktop-entry',
        action='store_false',
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

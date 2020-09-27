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

from .bubblejail_directories import BubblejailDirectories
from .services import SERVICES_CLASSES


def run_bjail(args: Namespace) -> None:
    instance_name = args.instance_name

    instance = BubblejailDirectories.instance_get(instance_name)

    if instance.is_running():
        if args.dry_run:
            print('Found helper socket.')
            print('Args to be send: ', args.args_to_instance)
            return

        command_return_text = async_run(
            instance.send_run_rpc(
                args_to_run=args.args_to_instance,
                wait_for_responce=args.wait,
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


def bjail_list(args: Namespace) -> None:
    if args.list_what == 'instances':
        for x in BubblejailDirectories.iter_instances_path():
            print(x.name)
    elif args.list_what == 'profiles':
        for profiles_directory in BubblejailDirectories.\
                iter_profile_directories():

            for profile_file in profiles_directory.iterdir():
                print(profile_file.stem)
    elif args.list_what == 'services':
        for service in SERVICES_CLASSES:
            print(service.name)


def bjail_create(args: Namespace) -> None:
    BubblejailDirectories.create_new_instance(
        new_name=args.new_instance_name,
        profile_name=args.profile,
        create_dot_desktop=args.no_desktop_entry,
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
    subparcers = parser.add_subparsers(
        required=True,
    )
    # run subcommand
    parser_run = subparcers.add_parser('run')

    parser_run.add_argument('--debug-shell', action='store_true')
    parser_run.add_argument('--dry-run', action='store_true')
    parser_run.add_argument('--debug-helper-script', type=Path)
    parser_run.add_argument('--debug-log-dbus', action='store_true')
    parser_run.add_argument('--wait', action='store_true')

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
        '--do-import',
        action='store_true',
    )
    parser_create.add_argument(
        '--import-from-instance',
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
        choices=('instances', 'profiles', 'services'),
        default='instances',)
    parser_list.set_defaults(func=bjail_list)

    # Edit subcommand
    parser_edit = subparcers.add_parser('edit')
    parser_edit.add_argument('instance_name')
    parser_edit.set_defaults(func=bjail_edit)

    # Generate desktop entry subcommand
    parser_desktop_entry = subparcers.add_parser('generate-desktop-entry')
    parser_desktop_entry.add_argument(
        '--profile',
    )
    parser_desktop_entry.add_argument(
        '--desktop-entry'
    )
    parser_desktop_entry.add_argument('instance_name')
    parser_desktop_entry.set_defaults(func=bjail_create_desktop_entry)

    args = parser.parse_args()

    args.func(args)

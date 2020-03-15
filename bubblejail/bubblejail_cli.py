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
from typing import Dict, Iterator, List, Union

from pkg_resources import resource_filename
from toml import load as toml_load

from .bubblejail_instance import BubblejailInstance
from .bubblejail_utils import BubblejailInstanceConfig, BubblejailProfile
from .exceptions import ServiceUnavalibleError


def iter_instance_names() -> Iterator[str]:
    data_dir = BubblejailInstance.get_instances_dir()
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


def get_profiles_dir() -> Path:
    return Path(resource_filename(__name__, 'profiles'))


def bjail_list(args: Namespace) -> None:
    if args.list_what == 'instances':
        for x in iter_instance_names():
            print(x)
    elif args.list_what == 'profiles':
        for profile_file in get_profiles_dir().iterdir():
            print(profile_file.stem)


def load_profile(profile_name: str) -> BubblejailProfile:
    with open(get_profiles_dir() / f"{profile_name}.toml") as f:
        return BubblejailProfile(**toml_load(f))


def bjail_create(args: Namespace) -> None:
    if args.profile is None:
        profile = BubblejailProfile()
    else:
        profile = load_profile(args.profile)

    if args.import_from_instance is not None:
        do_import_data = True
    else:
        do_import_data = args.do_import

    create_coroutine = BubblejailInstance.create_new(
        new_name=args.new_instance_name,
        profile=profile,
        create_dot_desktop=args.no_desktop_entry,
        do_import_data=do_import_data,
        import_from_instance=args.import_from_instance,
    )
    async_run(create_coroutine)


def bjail_edit(args: Namespace) -> None:
    async_run(BubblejailInstance(args.instance_name).edit_config_in_editor())


def bjail_auto_create(args: Namespace) -> None:
    profiles_to_create: Dict[str, BubblejailProfile] = {}
    instances_executables: Dict[Union[str, List[str], None], str] = {
        None: '',
    }
    # Read instances executables
    for instance_dir in BubblejailInstance.get_instances_dir().iterdir():
        with open(instance_dir / 'config.toml') as f:
            instance_conf = BubblejailInstanceConfig(**toml_load(f))

        instance_name = instance_dir.name
        instance_executable = instance_conf.executable_name
        if isinstance(instance_executable, list):
            instance_executable = instance_executable[0]

        instances_executables[instance_executable] = instance_name

    # Read profiles executable names
    for profile_file in get_profiles_dir().iterdir():
        profile_name = profile_file.stem
        with open(profile_file) as f:
            profile_entry = BubblejailProfile(**toml_load(f))

        profile_executable = profile_entry.config['executable_name']
        # If profile executable is a list take first item as executable
        if isinstance(profile_executable, list):
            profile_executable = profile_executable[0]

        if not Path(profile_executable).exists():
            print(f"Skipping {profile_name} as executable does not exist")
            continue

        try:
            profile_entry.get_config().verify()
        except ServiceUnavalibleError:
            print(
                f"Skipping {profile_name} "
                "as one of the services is unavalible")
            continue

        if profile_executable in instances_executables:
            print(f"Skipping {profile_name}"
                  " as instance with same executable already exists")
            continue

        profiles_to_create[profile_name] = profile_entry

    for profile_name, profile_entry in profiles_to_create.items():
        do_create_answer = input(
            f"Create {profile_name} instance? y/N: ")

        if do_create_answer.lower() != 'y':
            continue

        create_coroutine = BubblejailInstance.create_new(
            new_name=profile_name,
            profile=profile_entry,
            create_dot_desktop=True,
        )
        async_run(create_coroutine)


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
        choices=('instances', 'profiles'),
        default='instances',)
    parser_list.set_defaults(func=bjail_list)

    # Edit subcommand
    parser_edit = subparcers.add_parser('edit')
    parser_edit.add_argument('instance_name')
    parser_edit.set_defaults(func=bjail_edit)

    # Auto-create subcommand
    parser_auto_create = subparcers.add_parser('auto-create')
    parser_auto_create.set_defaults(func=bjail_auto_create)

    args = parser.parse_args()

    args.func(args)

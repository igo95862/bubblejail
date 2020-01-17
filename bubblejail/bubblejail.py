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


from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from json import load as json_load
from os import environ
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from tempfile import TemporaryFile
from typing import IO, Iterator, List, Optional

from .bubblejail_instance import BubblejailInstance
from .bwrap_config import DEFAULT_CONFIG, Bind, BwrapArgs
from .exceptions import BubblejailException
from .profiles import applications


@dataclass
class InstanceConfig:
    profile_name: str
    virt_home: Optional[str] = None


def get_config_directory() -> Path:
    # Check if XDG_CONFIG_HOME is set
    try:
        config_path = Path(environ['XDG_CONFIG_HOME'] + "/bubblejail")
    except KeyError:
        # Default to ~/.config/bubblejail
        config_path = Path(Path.home(), ".config/bubblejail")

    # Create directory if neccesary
    if not config_path.exists():
        config_path.mkdir(mode=0o700)

    return config_path


def get_data_directory() -> Path:
    # Check if XDG_DATA_HOME is set
    try:
        data_path = Path(environ['XDG_DATA_HOME'] + "/bubblejail")
    except KeyError:
        # Default to ~/.local/share/bubblejail
        data_path = Path(Path.home(), ".local/share/bubblejail")

    # Create directory if neccesary
    if not data_path.is_dir():
        data_path.mkdir(mode=0o700)

    return data_path


def copy_data_to_temp_file(data: bytes) -> IO[bytes]:
    temp_file = TemporaryFile()
    temp_file.write(data)
    temp_file.seek(0)
    return temp_file


def run_bwrap(args_to_target: List[str],
              bwrap_config: BwrapArgs = DEFAULT_CONFIG) -> 'Popen[bytes]':
    bwrap_args: List[str] = ['bwrap']

    for bind_entity in bwrap_config.binds:
        bwrap_args.extend(bind_entity.to_args())

    for ro_entity in bwrap_config.read_only_binds:
        bwrap_args.extend(ro_entity.to_args())

    for dir_entity in bwrap_config.dir_create:
        bwrap_args.extend(dir_entity.to_args())

    for symlink in bwrap_config.symlinks:
        bwrap_args.extend(symlink.to_args())

    # Proc
    bwrap_args.extend(('--proc', '/proc'))
    # Devtmpfs
    bwrap_args.extend(('--dev', '/dev'))
    # Unshare all
    bwrap_args.append('--unshare-all')
    # Die with parent
    bwrap_args.append('--die-with-parent')

    if bwrap_config.share_network:
        bwrap_args.append('--share-net')

    # Copy files
    # Prevent our temporary file from being garbage collected
    temp_files: List[IO[bytes]] = []
    file_descriptors_to_pass: List[int] = []
    for f in bwrap_config.files:
        temp_f = copy_data_to_temp_file(f.content)
        temp_files.append(temp_f)
        temp_file_descriptor = temp_f.fileno()
        file_descriptors_to_pass.append(temp_file_descriptor)
        bwrap_args.extend(('--file', str(temp_file_descriptor), f.dest))

    # Unset all variables
    for e in environ:
        if e not in bwrap_config.env_no_unset:
            bwrap_args.extend(('--unsetenv', e))

    # Set enviromental variables
    for env_var in bwrap_config.enviromental_variables:
        bwrap_args.extend(env_var.to_args())

    # Change directory
    bwrap_args.extend(('--chdir', '/home/user'))
    # Append extra args
    args_to_target.extend(bwrap_config.extra_args)
    bwrap_args.extend(args_to_target)
    p = Popen(bwrap_args, pass_fds=file_descriptors_to_pass,
              stdout=PIPE, stderr=STDOUT)
    print("Bubblewrap started")
    try:
        while True:
            print(p.communicate())
    except ValueError:
        print("Bubblewrap terminated")

    return p


def get_home_bind(instance_name: str) -> Bind:
    data_dir = get_data_directory()
    home_path = data_dir / instance_name
    if not home_path.exists():
        home_path.mkdir(mode=0o700)

    return Bind(str(home_path), '/home/user')


def load_instance(instance_name: str) -> InstanceConfig:
    config_dir = get_config_directory()
    instance_config_file = config_dir / (instance_name+'.json')
    if not instance_config_file.is_file():
        raise BubblejailException("Failed to find instance config file")

    with instance_config_file.open() as icf:
        instance_config = InstanceConfig(**json_load(icf))

    return instance_config


def run_instance(instance: BubblejailInstance) -> None:
    app_profile = applications[instance._read_config()]
    args = [app_profile.executable_name]

    if instance.args_to_run is not None:
        args.extend(instance.args_to_run)

    run_bwrap(args,
              app_profile.generate_bw_args(
                  home_path=instance.instance_directory / 'home',
                  instance=instance))


def iter_instance_names() -> Iterator[str]:
    data_dir = get_data_directory()
    for x in data_dir.iterdir():
        if x.is_dir():
            yield str(x.stem)


def run_bjail(args: Namespace) -> None:
    instance_name = args.instance_name
    run_instance(BubblejailInstance(instance_name, args.args_to_instance))


def bjail_list(args: Namespace) -> None:
    if args.list_what == 'instances':
        for x in iter_instance_names():
            print(x)
    elif args.list_what == 'profiles':
        for x in applications:
            print(x)


def bjail_create(args: Namespace) -> None:
    new_instance = BubblejailInstance.create_new(
        new_name=args.new_instance_name,
        profile_name=args.profile,
    )
    new_instance.generate_dot_desktop(
        (f"/usr/share/applications/"
         f"{applications[new_instance._read_config()].executable_name}"
         f".desktop")
    )


def main() -> None:
    parser = ArgumentParser()
    subparcers = parser.add_subparsers()
    # run subcommand
    parser_run = subparcers.add_parser('run')
    parser_run.add_argument('instance_name')
    parser_run.add_argument(
        'args_to_instance',
        nargs='*',
    )
    parser_run.set_defaults(func=run_bjail)
    # create subcommand
    parser_create = subparcers.add_parser('create')
    parser_create.set_defaults(func=bjail_create)
    parser_create.add_argument(
        '--profile',
        choices=applications.keys(),
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

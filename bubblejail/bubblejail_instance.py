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

from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE as asyncio_pipe
from asyncio.subprocess import STDOUT as asyncio_stdout
from json import dump as json_dump
from json import load as json_load
from os import environ
from pathlib import Path
from socket import AF_UNIX, SOCK_STREAM, SocketType, socket
from subprocess import run as sub_run  # nosec
from tempfile import TemporaryFile
from typing import IO, Iterator, List, Optional, Set

from xdg import IniFile
from xdg.BaseDirectory import xdg_data_home
from xdg.Exceptions import NoKeyError as XdgNoKeyError

from .bubblejail_instance_config import BubblejailInstanceConfig
from .bwrap_config import DEFAULT_CONFIG, Bind, BwrapConfig
from .exceptions import BubblejailException
from .profiles import PROFILES
from .services import SERVICES


def copy_data_to_temp_file(data: bytes) -> IO[bytes]:
    temp_file = TemporaryFile()
    temp_file.write(data)
    temp_file.seek(0)
    return temp_file


def get_data_directory() -> Path:
    data_path = Path(xdg_data_home + "/bubblejail")

    # Create directory if neccesary
    if not data_path.is_dir():
        data_path.mkdir(mode=0o700)

    return data_path


class BubblejailInstance:
    def __init__(self, name: str):
        self.name = name

        # Prevent our temporary file from being garbage collected
        self.temp_files: List[IO[bytes]] = []

        # Unix Socket
        self.socket: Optional[SocketType] = None
        self.socket_path: Optional[Path] = None

        self.instance_directory = get_data_directory() / self.name

        if not self.instance_directory.exists():
            raise BubblejailException("Instance directory does not exist")

        instance_config = self._read_config()
        self.executable_name = instance_config.executable_name
        self.services_config = instance_config.services

    def _read_config(self) -> BubblejailInstanceConfig:
        with (self.instance_directory / "config.json").open() as f:
            return BubblejailInstanceConfig(**json_load(f))

    def generate_dot_desktop(self, dot_desktop_path: str) -> None:
        new_dot_desktop = IniFile.IniFile(
            filename=dot_desktop_path)

        # Strip non Desktop Entry groups
        # TODO: Modify actions instead of removing
        groups_to_remove = []
        for g in new_dot_desktop.groups():
            if g != "Desktop Entry":
                groups_to_remove.append(g)

        for g in groups_to_remove:
            new_dot_desktop.removeGroup(g)

        # Remove Actions= from Desktop Entry
        try:
            new_dot_desktop.removeKey(
                key='Actions',
                group='Desktop Entry'
            )
        except XdgNoKeyError:
            ...
        # Modify Exec
        old_exec = new_dot_desktop.get(
            key='Exec', group='Desktop Entry'
        )

        new_dot_desktop.set(
            key='Exec',
            value=(f"bubblejail run {self.name} "
                   f"{' '.join(old_exec.split()[1:])}"),
            group='Desktop Entry')

        # Modify name
        new_dot_desktop.set(
            key="Name",
            group='Desktop Entry',
            value=f"{self.name} bubble",
        )

        # Modify StartupWMClass
        new_dot_desktop.set(
            key="StartupWMClass",
            group='Desktop Entry',
            value=f"bubble_{self.name}",
        )

        dot_desktop_path = (
            f"{xdg_data_home}/applications/bubble_{self.name}.desktop")

        new_dot_desktop.write(filename=dot_desktop_path)

    @staticmethod
    def create_new(new_name: str, profile_name: str) -> 'BubblejailInstance':
        instance_directory = get_data_directory() / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700)
        # Make home directory
        (instance_directory / 'home').mkdir(mode=0o700)
        # Make config.json
        with (instance_directory / 'config.json').open(mode='x') as inst_cf:
            profile = PROFILES[profile_name]

            default_config = profile.default_instance_config

            # Update service keys

            for service_dict in default_config.services.values():
                key_updates = {}
                for key in service_dict:
                    if key == 'name':
                        key_updates[key] = new_name

                service_dict.update(key_updates)

            json_dump(default_config.__dict__, inst_cf, indent=2)

        instance = BubblejailInstance(new_name)
        return instance

    def iter_bwrap_configs(self) -> Iterator[BwrapConfig]:
        yield DEFAULT_CONFIG
        for service_name, service_conf in self.services_config.items():
            yield SERVICES[service_name](**service_conf)

        # Bind home
        yield BwrapConfig(
            binds=(Bind(str(self.instance_directory / 'home'), '/home/user/'),
                   )
        )

    async def async_run(
        self,
        args_to_run: Optional[List[str]] = None,
        debug_print_args: bool = False,
        debug_shell: bool = False,
        dry_run: bool = False,
    ) -> None:
        try:
            await self.init_bwrap(
                args_to_run=args_to_run,
                debug_print_args=debug_print_args,
                debug_shell=debug_shell,
                dry_run=dry_run,
            )
        finally:
            # Cleanup
            for t in self.temp_files:
                t.close()

            if self.socket_path is not None:
                self.socket_path.unlink()

            if self.socket is not None:
                self.socket.close()

    async def init_bwrap(
        self,
        args_to_run: Optional[List[str]] = None,
        debug_print_args: bool = False,
        debug_shell: bool = False,
        dry_run: bool = False,
    ) -> None:
        bwrap_args: List[str] = ['bwrap']

        extra_args: List[str] = []
        env_no_unset: Set[str] = set()

        share_network: bool = False

        file_descriptors_to_pass: List[int] = []

        for bwrap_config in self.iter_bwrap_configs():
            for bind_entity in bwrap_config.binds:
                bwrap_args.extend(bind_entity.to_args())

            for ro_entity in bwrap_config.read_only_binds:
                bwrap_args.extend(ro_entity.to_args())

            for dir_entity in bwrap_config.dir_create:
                bwrap_args.extend(dir_entity.to_args())

            for symlink in bwrap_config.symlinks:
                bwrap_args.extend(symlink.to_args())

            if bwrap_config.share_network:
                share_network = True

            # Copy files
            for f in bwrap_config.files:
                temp_f = copy_data_to_temp_file(f.content)
                self.temp_files.append(temp_f)
                temp_file_descriptor = temp_f.fileno()
                file_descriptors_to_pass.append(temp_file_descriptor)
                bwrap_args.extend(
                    ('--file', str(temp_file_descriptor), f.dest))

            # Set enviromental variables
            for env_var in bwrap_config.enviromental_variables:
                bwrap_args.extend(env_var.to_args())
                # Put them in to no unset as well
                env_no_unset.add(env_var.var_name)

            # Append extra args
            extra_args.extend(bwrap_config.extra_args)

            # Add env vars to no unset set
            env_no_unset.update(bwrap_config.env_no_unset)

        # Proc
        bwrap_args.extend(('--proc', '/proc'))
        # Devtmpfs
        bwrap_args.extend(('--dev', '/dev'))
        # Unshare all
        bwrap_args.append('--unshare-all')
        # Die with parent
        bwrap_args.append('--die-with-parent')

        # Share network if set
        if share_network:
            bwrap_args.append('--share-net')

        # Unset all variables
        for e in environ:
            if e not in env_no_unset:
                bwrap_args.extend(('--unsetenv', e))

        # Change directory
        bwrap_args.extend(('--chdir', '/home/user'))

        if not debug_shell:
            # Add executable name
            if self.executable_name is None:
                raise ValueError("No executable")

            if isinstance(self.executable_name, str):
                bwrap_args.append(self.executable_name)
            else:
                bwrap_args.extend(self.executable_name)

            # Add extra args
            bwrap_args.extend(extra_args)
            # Add called args
            if args_to_run:
                bwrap_args.extend(args_to_run)
        else:
            # Run debug shell
            bwrap_args.append('/bin/sh')

        # Dump args if requested and exit
        if debug_print_args:
            print(' '.join(bwrap_args))

        if dry_run:
            return

        # Create and bind socket
        self.socket = socket(AF_UNIX, SOCK_STREAM)
        socket_dir = Path(environ['XDG_RUNTIME_DIR']) / 'bubblejail'
        socket_dir.mkdir(mode=0o700, exist_ok=True)
        self.socket_path = socket_dir / self.name
        self.socket.bind(str(self.socket_path))
        # Bind socket inside sandbox

        if not debug_shell:
            p = await create_subprocess_exec(
                *bwrap_args, pass_fds=file_descriptors_to_pass,
                stdout=asyncio_pipe, stderr=asyncio_stdout)
            print("Bubblewrap started")
            print(await p.communicate())
            print("Bubblewrap terminated")
        else:
            print("Starting debug shell")
            sub_run(  # nosec
                args=bwrap_args,
                pass_fds=file_descriptors_to_pass,
            )
            print("Debug shell ended")

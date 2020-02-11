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

from asyncio import create_subprocess_exec, create_task
from asyncio.subprocess import DEVNULL as asyncio_devnull
from asyncio.subprocess import PIPE as asyncio_pipe
from asyncio.subprocess import STDOUT as asyncio_stdout
from asyncio.subprocess import Process
from json import dump as json_dump
from json import load as json_load
from os import environ
from pathlib import Path
from socket import AF_UNIX, SOCK_STREAM, SocketType, socket
from subprocess import run as sub_run  # nosec
from tempfile import TemporaryFile
from typing import IO, Iterator, List, Optional, Set, Tuple

from xdg import IniFile
from xdg.BaseDirectory import get_runtime_dir, xdg_data_home
from xdg.Exceptions import NoKeyError as XdgNoKeyError

from .bubblejail_instance_config import BubblejailInstanceConfig
from .bwrap_config import Bind, BwrapConfig, EnvrimentalVar
from .exceptions import BubblejailException
from .profiles import PROFILES
from .services import DEFAULT_CONFIG, SERVICES


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
        self.file_descriptors_to_pass: List[int] = []

        # Unix Socket
        self.socket: Optional[SocketType] = None
        self.socket_path: Optional[Path] = None
        # Dbus session proxy path
        self.dbus_session_socket: Optional[SocketType] = None
        self.dbus_session_socket_path: Optional[Path] = None

        self.instance_directory = get_data_directory() / self.name
        self.runtime_dir: Optional[Path] = None

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
    def create_new(
            new_name: str,
            profile_name: Optional[str] = None
    ) -> 'BubblejailInstance':
        instance_directory = get_data_directory() / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700)
        # Make home directory
        (instance_directory / 'home').mkdir(mode=0o700)
        # Make config.json
        with (instance_directory / 'config.json').open(mode='x') as inst_cf:
            if profile_name is not None:
                profile = PROFILES[profile_name]
                default_config = profile.default_instance_config
            else:
                default_config = BubblejailInstanceConfig()

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

        # Bind home
        yield BwrapConfig(
            binds=(Bind(str(self.instance_directory / 'home'), '/home/user/'),
                   )
        )

        for service_name, service_conf in self.services_config.items():
            yield SERVICES[service_name](**service_conf)

    def get_runtime_dir_path(self) -> Path:
        return Path(get_runtime_dir() + f'/bubblejail/{self.name}')

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

            if self.dbus_session_socket_path is not None:
                self.dbus_session_socket_path.unlink()

            if self.dbus_session_socket is not None:
                self.dbus_session_socket.close()

            if self.runtime_dir is not None:
                self.runtime_dir.rmdir()

    def genetate_args(
        self,
        args_to_run: Optional[List[str]] = None,
        debug_print_args: bool = False,
        debug_shell: bool = False
    ) -> Tuple[List[str], List[str]]:
        # TODO: Reorganize the order to allow for
        # better binding multiple resources in same filesystem path
        bwrap_args: List[str] = ['bwrap']
        dbus_session_args: List[str] = []

        dbus_session_opts: Set[str] = set()

        extra_args: List[str] = []
        env_no_unset: Set[str] = set()

        share_network: bool = False

        # Proc
        bwrap_args.extend(('--proc', '/proc'))
        # Devtmpfs
        bwrap_args.extend(('--dev', '/dev'))
        # Unshare all
        bwrap_args.append('--unshare-all')
        # Die with parent
        bwrap_args.append('--die-with-parent')

        # Unset all variables
        for e in environ:
            bwrap_args.extend(('--unsetenv', e))

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
                self.file_descriptors_to_pass.append(temp_file_descriptor)
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

            for e in bwrap_config.env_no_unset:
                try:
                    bwrap_args.extend(('--setenv', e, environ[e]))
                except KeyError:
                    if __debug__:
                        print(f'Env {e} is not set.')

            # Add dbus session args
            for de in bwrap_config.dbus_session:
                dbus_session_opts.update(de.to_args())

        # If we found any dbus args
        if dbus_session_opts:
            print('Dbus args found')
            env_dbus_session_addr = 'DBUS_SESSION_BUS_ADDRESS'
            self.dbus_session_socket_path = (
                self.get_runtime_dir_path() / 'dbus_session_proxy')

            dbus_session_args = [
                'xdg-dbus-proxy',
                environ[env_dbus_session_addr],
                str(self.dbus_session_socket_path),
            ]
            dbus_session_args.extend(dbus_session_opts)
            dbus_session_args.append('--filter')
            dbus_session_args.append('--log')

            # Bind socket inside the sandbox
            bwrap_args.extend(
                EnvrimentalVar(
                    env_dbus_session_addr,
                    'unix:path=/run/user/1000/bus').to_args()
            )

            bwrap_args.extend(
                Bind(
                    str(self.dbus_session_socket_path),
                    '/run/user/1000/bus').to_args()
            )

        # Share network if set
        if share_network:
            bwrap_args.append('--share-net')

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

        # Dump args if requested
        if debug_print_args:
            print(' '.join(bwrap_args))

        return bwrap_args, dbus_session_args

    async def bwrap_watcher(self, bwrap_procces: Process) -> None:
        """Reads stdout of bwrap and prints"""
        bwrap_stdout = bwrap_procces.stdout

        if bwrap_stdout is None:
            return

        while True:
            new_line_data = await bwrap_stdout.readline()
            if new_line_data:
                print(new_line_data)
            else:
                return

    async def init_bwrap(
        self,
        args_to_run: Optional[List[str]] = None,
        debug_print_args: bool = False,
        debug_shell: bool = False,
        dry_run: bool = False,
    ) -> None:
        bwrap_args, dbus_session_proxy_args = self.genetate_args(
            debug_print_args=debug_print_args,
            debug_shell=debug_shell,)

        if dry_run:
            return

        # Create runtime dir
        # If the dir exists exception will be raised inidicating that
        # instance is already running or did not clean-up properly.
        self.runtime_dir = self.get_runtime_dir_path()
        self.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=False)

        # Create and bind helper socket
        self.socket = socket(AF_UNIX, SOCK_STREAM)
        self.socket_path = self.runtime_dir / 'helper_socket'
        self.socket.bind(str(self.socket_path))
        # Bind socket inside sandbox
        # TODO: Helper socket

        # Dbus session proxy
        if dbus_session_proxy_args:
            self.dbus_session_socket = socket(AF_UNIX, SOCK_STREAM)
            self.dbus_session_socket.bind(str(self.dbus_session_socket_path))

            # Pylint does not recognize *args for some reason
            # pylint: disable=E1120
            dbus_session_proxy_process = await create_subprocess_exec(
                *dbus_session_proxy_args,
                stdout=asyncio_pipe if not debug_shell else asyncio_devnull,
                stderr=asyncio_stdout,
            )

            create_task(
                self.bwrap_watcher(dbus_session_proxy_process),
                name='dbus session proxy',
            )

        if not debug_shell:
            p = await create_subprocess_exec(
                *bwrap_args, pass_fds=self.file_descriptors_to_pass,
                stdout=asyncio_pipe, stderr=asyncio_stdout)
            print("Bubblewrap started")
            task_bwrap_main = create_task(
                self.bwrap_watcher(p), name='bwrap main')
            await task_bwrap_main
            print("Bubblewrap terminated")
        else:
            print("Starting debug shell")
            sub_run(  # nosec
                args=bwrap_args,
                pass_fds=self.file_descriptors_to_pass,
            )
            print("Debug shell ended")

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

from asyncio import (CancelledError, Task, create_subprocess_exec, create_task,
                     open_unix_connection)
from asyncio.subprocess import DEVNULL as asyncio_devnull
from asyncio.subprocess import PIPE as asyncio_pipe
from asyncio.subprocess import STDOUT as asyncio_stdout
from asyncio.subprocess import Process
from os import environ
from pathlib import Path
from socket import AF_UNIX, SOCK_STREAM, SocketType, socket
from tempfile import TemporaryFile
from typing import IO, Any, Iterator, List, Optional, Set, Type

from toml import dump as toml_dump
from toml import load as toml_load
from xdg import IniFile
from xdg.BaseDirectory import get_runtime_dir, xdg_data_home
from xdg.Exceptions import NoKeyError as XdgNoKeyError

from .bubblejail_helper import RequestRun
from .bubblejail_instance_config import BubblejailInstanceConfig
from .bwrap_config import (Bind, BwrapConfigBase, DbusSessionTalkTo,
                           EnvrimentalVar, FileTransfer)
from .exceptions import BubblejailException
from .profiles import PROFILES
from .services import SERVICES, BubblejailDefaults, BubblejailService


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


async def process_watcher(process: Process) -> None:
    """Reads stdout of process and prints"""
    process_stdout = process.stdout

    if __debug__:
        print(f"Watching {repr(process)}")

    if process_stdout is None:
        return

    while True:
        new_line_data = await process_stdout.readline()

        if new_line_data:
            print(new_line_data)
        else:
            return


class BubblejailInstance:
    def __init__(self, name: str):
        self.name = name
        # Instance directory located at $XDG_DATA_HOME/bubblejail/
        self.instance_directory = get_data_directory() / self.name
        self.home_bind_path = self.instance_directory / 'home'
        # If instance directory does not exists we can't do much
        # Probably someone used 'run' command before 'create'
        if not self.instance_directory.exists():
            raise BubblejailException("Instance directory does not exist")

        # Run-time directory
        self.runtime_dir: Path = Path(
            get_runtime_dir() + f'/bubblejail/{self.name}')

        # Helper run-time directory
        self.helper_runtime_dir: Path = self.runtime_dir / 'helper'

        # Unix Socket used to communicate with helper
        self.helper_socket_path: Path = (
            self.helper_runtime_dir / 'helper.socket')
        # Dbus session proxy path
        self.dbus_session_socket_path: Path = (
            self.runtime_dir / 'dbus_session_proxy')

    def _read_config(self) -> BubblejailInstanceConfig:
        with (self.instance_directory / "config.toml").open() as f:
            return BubblejailInstanceConfig(**toml_load(f))

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
        with (instance_directory / 'config.toml').open(mode='x') as inst_cf:
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

            toml_dump(default_config.__dict__, inst_cf)

        instance = BubblejailInstance(new_name)
        return instance

    async def send_run_rpc(self, args_to_run: List[str]) -> None:
        (_, writter) = await open_unix_connection(
            path=self.helper_socket_path,
        )

        request = RequestRun(
            args_to_run=args_to_run,
        )
        writter.write(request.to_json_byte_line())
        await writter.drain()

        writter.close()
        await writter.wait_closed()

    async def async_run(
        self,
        args_to_run: List[str],
        debug_shell: bool = False,
        dry_run: bool = False,
        debug_helper_script: Optional[Path] = None,
        debug_log_dbus: bool = False,
    ) -> None:

        instance_config = self._read_config()

        # Insert the executable name
        if isinstance(instance_config.executable_name, str):
            args_to_run.insert(0, instance_config.executable_name)
        elif isinstance(instance_config.executable_name, list):
            new_arg_list = instance_config.executable_name
            new_arg_list.extend(args_to_run)
            args_to_run = new_arg_list

        # Use IPC to run new command inside the namespace
        if self.helper_socket_path.exists():
            if not dry_run:
                await self.send_run_rpc(args_to_run)
            else:
                print('Found helper socket.')
                print('Args to be send: ', args_to_run)

            return

        # Create init
        init = BubblejailInit(
            parent=self,
            instance_config=instance_config,
            is_shell_debug=debug_shell,
            is_helper_debug=debug_helper_script is not None,
            is_log_dbus=debug_log_dbus,
        )

        async with init:
            if dry_run:
                print('Bwrap args: ')
                print(' '.join(init.bwrap_args))

                if init.dbus_session_args:
                    print('Dbus session args')
                    print(' '.join(init.dbus_session_args))

                return

            if debug_helper_script is not None:
                with open(debug_helper_script) as f:
                    script_text = f.read()

                init.bwrap_args.append(script_text)

            if debug_shell:
                args_to_run = ['--shell']

            process = await create_subprocess_exec(
                *init.bwrap_args, *args_to_run,
                pass_fds=init.file_descriptors_to_pass,
                stdout=(asyncio_pipe
                        if not debug_shell
                        else None),
                stderr=asyncio_stdout,
            )
            if __debug__:
                print(f"Bubblewrap started. PID: {repr(process)}")

            if not debug_shell:
                task_bwrap_main = create_task(
                    process_watcher(process), name='bwrap main')
                await task_bwrap_main
            else:
                print("Starting debug shell")
                await process.wait()
                print("Debug shell ended")

            if __debug__:
                print("Bubblewrap terminated")


class BubblejailInit:
    def __init__(
        self,
        parent: BubblejailInstance,
        instance_config: BubblejailInstanceConfig,
        is_shell_debug: bool = False,
        is_helper_debug: bool = False,
        is_log_dbus: bool = False,
    ) -> None:
        self.home_bind_path = parent.home_bind_path
        self.runtime_dir = parent.runtime_dir
        # Prevent our temporary file from being garbage collected
        self.temp_files: List[IO[bytes]] = []
        self.file_descriptors_to_pass: List[int] = []
        # Helper
        self.helper_runtime_dir = parent.helper_runtime_dir
        self.helper_socket_path = parent.helper_socket_path
        # Dbus socket needs to be cleaned up
        self.dbus_session_socket: Optional[SocketType] = None
        self.dbus_session_socket_path = parent.dbus_session_socket_path
        # Args to dbus proxy
        self.dbus_session_args: List[str] = []
        self.dbus_session_proxy_process: Optional[Process] = None
        # Args to bwrap
        self.bwrap_args: List[str] = []
        # Debug mode
        self.is_helper_debug = is_helper_debug
        self.is_shell_debug = is_shell_debug
        self.is_log_dbus = is_log_dbus
        # Instance config
        self.instance_config = instance_config

        # Tasks
        self.watch_dbus_proxy_task: Optional[Task[None]] = None

    def iter_bwrap_configs(self) -> Iterator[BubblejailService]:
        yield BubblejailDefaults(self.home_bind_path)

        for service_name, service_conf in (
                self.instance_config.services.items()):
            yield SERVICES[service_name](**service_conf)

    def genetate_args(self) -> None:
        # TODO: Reorganize the order to allow for
        # better binding multiple resources in same filesystem path
        self.bwrap_args.append('bwrap')

        dbus_session_opts: Set[str] = set()

        # Unshare all
        self.bwrap_args.append('--unshare-all')
        # Die with parent
        self.bwrap_args.append('--die-with-parent')

        # Set user and group id to pseudo user
        self.bwrap_args.extend(
            ('--uid', '1000', '--gid', '1000')
        )

        # Proc
        self.bwrap_args.extend(('--proc', '/proc'))
        # Devtmpfs
        self.bwrap_args.extend(('--dev', '/dev'))

        # Unset all variables
        for e in environ:
            self.bwrap_args.extend(('--unsetenv', e))

        for bwrap_config in self.iter_bwrap_configs():

            for config in bwrap_config:
                if isinstance(config, BwrapConfigBase):
                    self.bwrap_args.extend(config.to_args())
                elif isinstance(config, FileTransfer):
                    # Copy files
                    temp_f = copy_data_to_temp_file(config.content)
                    self.temp_files.append(temp_f)
                    temp_file_descriptor = temp_f.fileno()
                    self.file_descriptors_to_pass.append(
                        temp_file_descriptor)
                    self.bwrap_args.extend(
                        ('--file', str(temp_file_descriptor), config.dest))
                elif isinstance(config, DbusSessionTalkTo):
                    dbus_session_opts.update(config.to_args())

        # If we found any dbus args
        if dbus_session_opts:
            if __debug__:
                print('Dbus args found')
            env_dbus_session_addr = 'DBUS_SESSION_BUS_ADDRESS'

            self.dbus_session_args.extend((
                'xdg-dbus-proxy',
                environ[env_dbus_session_addr],
                str(self.dbus_session_socket_path),
            ))
            self.dbus_session_args.extend(dbus_session_opts)
            self.dbus_session_args.append('--filter')
            if self.is_log_dbus:
                self.dbus_session_args.append('--log')

            # Bind socket inside the sandbox
            self.bwrap_args.extend(
                EnvrimentalVar(
                    env_dbus_session_addr,
                    'unix:path=/run/user/1000/bus').to_args()
            )
            self.bwrap_args.extend(
                Bind(
                    str(self.dbus_session_socket_path),
                    '/run/user/1000/bus').to_args()
            )

        # Share network if set
        if 'network' in self.instance_config.services:
            self.bwrap_args.append('--share-net')

        # Bind helper directory
        self.bwrap_args.extend(
            Bind(str(self.helper_runtime_dir), '/run/bubblehelp').to_args())

        # Change directory
        self.bwrap_args.extend(('--chdir', '/home/user'))

        # Append command to bwrap depending on debug helper
        if self.is_helper_debug:
            self.bwrap_args.extend(('python', '-X', 'dev', '-c'))
        else:
            self.bwrap_args.append('bubblejail-helper')

    async def __aenter__(self) -> None:
        # Generate args
        self.genetate_args()

        # Create runtime dir
        # If the dir exists exception will be raised inidicating that
        # instance is already running or did not clean-up properly.
        self.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        # Create helper directory
        self.helper_runtime_dir.mkdir(mode=0o700)

        # Dbus session proxy
        if self.dbus_session_args:
            self.dbus_session_socket = socket(AF_UNIX, SOCK_STREAM)
            self.dbus_session_socket.bind(
                str(self.dbus_session_socket_path))

            # Pylint does not recognize *args for some reason
            # pylint: disable=E1120
            self.dbus_session_proxy_process = await create_subprocess_exec(
                *self.dbus_session_args,
                stdout=(asyncio_pipe
                        if not self.is_shell_debug
                        else asyncio_devnull),
                stderr=asyncio_stdout,
                stdin=asyncio_devnull,
            )

            self.watch_dbus_proxy_task = create_task(
                process_watcher(self.dbus_session_proxy_process),
                name='dbus session proxy',
            )

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc: BaseException,
        traceback: Any,  # ???: What type is traceback
    ) -> None:
        # Cleanup
        if (
            self.watch_dbus_proxy_task is not None
            and
            not self.watch_dbus_proxy_task.done()
        ):
            self.watch_dbus_proxy_task.cancel()
            try:
                await self.watch_dbus_proxy_task
            except CancelledError:
                ...

        if self.dbus_session_proxy_process is not None:
            self.dbus_session_proxy_process.terminate()
            await self.dbus_session_proxy_process.wait()

        for t in self.temp_files:
            t.close()

        if self.helper_socket_path.exists():
            self.helper_socket_path.unlink()

        self.helper_runtime_dir.rmdir()

        if self.dbus_session_socket_path.exists():
            self.dbus_session_socket_path.unlink()

        if self.dbus_session_socket is not None:
            self.dbus_session_socket.close()

        self.runtime_dir.rmdir()

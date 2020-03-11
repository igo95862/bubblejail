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
from shutil import copytree
from socket import AF_UNIX, SOCK_STREAM, SocketType, socket
from tempfile import TemporaryDirectory, TemporaryFile
from typing import IO, Any, Iterator, List, Optional, Set, Type

from toml import dump as toml_dump
from toml import loads as toml_loads
from xdg import IniFile
from xdg.BaseDirectory import get_runtime_dir, xdg_data_home

from .bubblejail_helper import RequestRun
from .bubblejail_utils import (BubblejailInstanceConfig, BubblejailProfile,
                               ImportConfig)
from .bwrap_config import (Bind, BwrapConfigBase, DbusSessionTalkTo,
                           EnvrimentalVar, FileTransfer)
from .exceptions import BubblejailException
from .services import BubblejailDefaults, BubblejailService


def copy_data_to_temp_file(data: bytes) -> IO[bytes]:
    temp_file = TemporaryFile()
    temp_file.write(data)
    temp_file.seek(0)
    return temp_file


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
    DATA_DIR = Path(xdg_data_home + "/bubblejail")
    DESKTOP_ENTRIES_DIR = Path(xdg_data_home + '/applications')

    def __init__(self, name: str):
        self.name = name
        # Instance directory located at $XDG_DATA_HOME/bubblejail/
        self.instance_directory = self.get_instances_dir() / self.name
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

    @classmethod
    def get_instances_dir(cls) -> Path:
        return cls.DATA_DIR / 'instances'

    @property
    def instance_config_file_path(self) -> Path:
        return self.instance_directory / "config.toml"

    def _read_config_file(self) -> str:
        with (self.instance_config_file_path).open() as f:
            return f.read()

    def _read_config(
            self,
            config_contents: Optional[str] = None) -> BubblejailInstanceConfig:

        if config_contents is None:
            config_contents = self._read_config_file()

        return BubblejailInstanceConfig(**toml_loads(config_contents))

    def generate_dot_desktop(self, dot_desktop_path: Optional[Path]) -> None:

        if dot_desktop_path is not None:
            new_dot_desktop = IniFile.IniFile(
                filename=str(dot_desktop_path))

            for group_name in new_dot_desktop.groups():
                # Modify Exec
                old_exec = new_dot_desktop.get(
                    key='Exec', group=group_name
                )
                if not old_exec:
                    continue

                new_dot_desktop.set(
                    key='Exec',
                    value=(f"bubblejail run {self.name} "
                           f"{' '.join(old_exec.split()[1:])}"),
                    group=group_name)

        else:
            new_dot_desktop = IniFile.IniFile()
            new_dot_desktop.addGroup('Desktop Entry')
            new_dot_desktop.set(
                key='Exec',
                value=f"bubblejail run {self.name}",
                group='Desktop Entry'
            )

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

        new_dot_desktop_path_str = str(
            self.DESKTOP_ENTRIES_DIR / f"bubble_{self.name}.desktop")

        new_dot_desktop.write(filename=new_dot_desktop_path_str)

    @classmethod
    def create_new(
            cls,
            new_name: str,
            profile: BubblejailProfile,
            create_dot_desktop: bool = False,
            do_import_data: bool = False,
            import_from_instance: Optional[str] = None,
    ) -> 'BubblejailInstance':

        home_directory: Optional[Path] = None
        if import_from_instance is not None:
            another_instance = BubblejailInstance(import_from_instance)
            home_directory = another_instance.home_bind_path

        instance_directory = cls.get_instances_dir() / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700, parents=True)
        # Make home directory
        (instance_directory / 'home').mkdir(mode=0o700)
        # Make config.json
        with (instance_directory / 'config.toml').open(
                mode='x') as instance_conf_file:

            toml_dump(profile.config, instance_conf_file)

        instance = BubblejailInstance(new_name)

        if do_import_data:
            instance.import_data(
                import_conf=profile.import_conf,
                home_dir=home_directory,
            )

        if create_dot_desktop:
            instance.generate_dot_desktop(profile.dot_desktop_path)

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

    async def edit_config_in_editor(self) -> None:
        # Create temporary directory
        with TemporaryDirectory() as tempdir:
            # Create path to temporary file and write exists config
            temp_file_path = Path(tempdir + 'temp.toml')
            with open(temp_file_path, mode='w') as tempfile:
                tempfile.write(self._read_config_file())
            # Launch EDITOR on the temporary file
            run_args = [environ['EDITOR'], str(temp_file_path)]
            p = await create_subprocess_exec(*run_args)
            await p.wait()
            # Verify that the new config is valid and save to variable
            with open(temp_file_path) as tempfile:
                new_config_toml = tempfile.read()
                conf_to_verify = BubblejailInstanceConfig(
                    **toml_loads(new_config_toml)
                )
                conf_to_verify.verify()
            # Write to instance config file
            with open(self.instance_config_file_path, mode='w') as conf_file:
                conf_file.write(new_config_toml)

    def import_data(self, import_conf: ImportConfig,
                    home_dir: Optional[Path]) -> None:
        if home_dir is None:
            home_dir = Path.home()

        for from_home_copy_path in import_conf.copy:
            copytree(
                src=(home_dir / from_home_copy_path),
                dst=(self.home_bind_path / from_home_copy_path),
            )


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
        yield BubblejailDefaults(
            home_bind_path=self.home_bind_path,
            share_local_time=self.instance_config.share_local_time,
        )

        yield from self.instance_config.iter_services()

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

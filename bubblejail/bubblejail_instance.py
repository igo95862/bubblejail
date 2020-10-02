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
                     open_unix_connection, wait_for)
from asyncio.subprocess import DEVNULL as asyncio_devnull
from asyncio.subprocess import PIPE as asyncio_pipe
from asyncio.subprocess import STDOUT as asyncio_stdout
from asyncio.subprocess import Process
from os import environ
from pathlib import Path
from socket import AF_UNIX, SOCK_STREAM, SocketType, socket
from tempfile import TemporaryDirectory, TemporaryFile
from typing import (IO, Any, List, MutableMapping, Optional, Set, Type,
                    TypedDict, cast)

from toml import dump as toml_dump
from toml import loads as toml_loads
from xdg.BaseDirectory import get_runtime_dir

from .bubblejail_helper import RequestRun
from .bubblejail_seccomp import SeccompState
from .bubblejail_utils import FILE_NAME_METADATA, FILE_NAME_SERVICES
from .bwrap_config import (Bind, BwrapConfigBase, DbusSessionArgs,
                           DbusSystemArgs, EnvrimentalVar, FileTransfer,
                           LaunchArguments, SeccompDirective)
from .exceptions import BubblejailException
from .services import ServiceContainer as BubblejailInstanceConfig
from .services import ServicesConfDictType, ServiceWantsHomeBind


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


class ConfDict(TypedDict, total=False):
    service: ServicesConfDictType
    services: List[str]
    executable_name: List[str]
    share_local_time: bool
    filter_disk_sync: bool


class BubblejailInstance:

    def __init__(self, instance_home: Path):
        self.name = instance_home.stem
        # Instance directory located at $XDG_DATA_HOME/bubblejail/
        self.instance_directory = instance_home
        # If instance directory does not exists we can't do much
        # Probably someone used 'run' command before 'create'
        if not self.instance_directory.exists():
            raise BubblejailException("Instance directory does not exist")

        # Run-time directory
        self.runtime_dir: Path = Path(
            get_runtime_dir() + f'/bubblejail/{self.name}')

    # region Paths

    @property
    def path_config_file(self) -> Path:
        return self.instance_directory / FILE_NAME_SERVICES

    @property
    def path_metadata_file(self) -> Path:
        return self.instance_directory / FILE_NAME_METADATA

    @property
    def path_home_directory(self) -> Path:
        return self.instance_directory / 'home'

    @property
    def path_runtime_helper_dir(self) -> Path:
        """Helper run-time directory"""
        return self.runtime_dir / 'helper'

    @property
    def path_runtime_helper_socket(self) -> Path:
        return self.path_runtime_helper_dir / 'helper.socket'

    @property
    def path_runtime_dbus_session_socket(self) -> Path:
        return self.runtime_dir / 'dbus_session_proxy'

    @property
    def path_runtime_dbus_system_socket(self) -> Path:
        return self.runtime_dir / 'dbus_system_proxy'

    # endregion Paths

    # region Metadata

    def _get_metadata_dict(self) -> MutableMapping[Any, Any]:
        try:
            with open(self.path_metadata_file) as metadata_file:
                return toml_loads(metadata_file.read())
        except FileNotFoundError:
            return {}

    def _save_metadata_key(self, key: str, value: Any) -> None:
        toml_dict = self._get_metadata_dict()
        toml_dict[key] = value

        with open(self.path_metadata_file, mode='w') as metadata_file:
            toml_dump(toml_dict, metadata_file)

    def _get_metadata_value(self, key: str) -> Optional[str]:
        try:
            value = self._get_metadata_dict()[key]
            if isinstance(value, str):
                return value
            else:
                raise TypeError(f"Expected str, got {value}")
        except KeyError:
            return None

    @property
    def metadata_creation_profile_name(self) -> Optional[str]:
        return self._get_metadata_value('creation_profile_name')

    @metadata_creation_profile_name.setter
    def metadata_creation_profile_name(self, profile_name: str) -> None:
        self._save_metadata_key(
            key='creation_profile_name',
            value=profile_name,
        )

    @property
    def metadata_desktop_entry_name(self) -> Optional[str]:
        return self._get_metadata_value('desktop_entry_name')

    @metadata_desktop_entry_name.setter
    def metadata_desktop_entry_name(self, desktop_entry_name: str) -> None:
        self._save_metadata_key(
            key='desktop_entry_name',
            value=desktop_entry_name,
        )

    # endregion Metadata

    def _read_config_file(self) -> str:
        with (self.path_config_file).open() as f:
            return f.read()

    def _read_config(
            self,
            config_contents: Optional[str] = None) -> BubblejailInstanceConfig:

        if config_contents is None:
            config_contents = self._read_config_file()

        conf_dict = cast(ServicesConfDictType, toml_loads(config_contents))

        return BubblejailInstanceConfig(conf_dict)

    def save_config(self, config: BubblejailInstanceConfig) -> None:
        with open(self.path_config_file, mode='w') as conf_file:
            toml_dump(config.get_service_conf_dict(), conf_file)

    async def send_run_rpc(
        self,
        args_to_run: List[str],
        wait_for_response: bool = False,
    ) -> Optional[str]:
        (reader, writer) = await open_unix_connection(
            path=self.path_runtime_helper_socket,
        )

        request = RequestRun(
            args_to_run=args_to_run,
            wait_response=wait_for_response,
        )
        writer.write(request.to_json_byte_line())
        await writer.drain()

        try:
            if wait_for_response:
                data: Optional[str] \
                    = request.decode_response(
                        await wait_for(
                            fut=reader.readline(),
                            timeout=3,
                        )
                )
            else:
                data = None
        finally:
            writer.close()
            await writer.wait_closed()

        return data

    def is_running(self) -> bool:
        return self.path_runtime_helper_socket.is_socket()

    async def async_run_init(
        self,
        args_to_run: List[str],
        debug_shell: bool = False,
        dry_run: bool = False,
        debug_helper_script: Optional[Path] = None,
        debug_log_dbus: bool = False,
    ) -> None:

        instance_config = self._read_config()

        # Create init
        init = BubblejailInit(
            parent=self,
            instance_config=instance_config,
            is_shell_debug=debug_shell,
            is_helper_debug=debug_helper_script is not None,
            is_log_dbus=debug_log_dbus,
        )

        async with init:
            if not args_to_run:
                args_to_run = init.executable_args

            if dry_run:
                print('Bwrap args: ')
                print(' '.join(init.bwrap_args), ' '.join(args_to_run))

                print('Dbus session args')
                print(' '.join(init.dbus_proxy_args))

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
                BubblejailInstanceConfig(
                    cast(ServicesConfDictType, toml_loads(new_config_toml))
                )
            # Write to instance config file
            with open(self.path_config_file, mode='w') as conf_file:
                conf_file.write(new_config_toml)


class BubblejailInit:
    def __init__(
        self,
        parent: BubblejailInstance,
        instance_config: BubblejailInstanceConfig,
        is_shell_debug: bool = False,
        is_helper_debug: bool = False,
        is_log_dbus: bool = False,
    ) -> None:
        self.home_bind_path = parent.path_home_directory
        self.runtime_dir = parent.runtime_dir
        # Prevent our temporary file from being garbage collected
        self.temp_files: List[IO[bytes]] = []
        self.file_descriptors_to_pass: List[int] = []
        # Helper
        self.helper_runtime_dir = parent.path_runtime_helper_dir
        self.helper_socket_path = parent.path_runtime_helper_socket

        # Args to dbus proxy
        self.dbus_proxy_args: List[str] = []
        self.dbus_proxy_process: Optional[Process] = None

        # Dbus session socket
        self.dbus_session_socket: Optional[SocketType] = None
        self.dbus_session_socket_path = parent.path_runtime_dbus_session_socket

        # Dbus system socket
        self.dbus_system_socket: Optional[SocketType] = None
        self.dbus_system_socket_path = parent.path_runtime_dbus_system_socket

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

        # Executable args
        self.executable_args: List[str] = []

    def genetate_args(self) -> None:
        # TODO: Reorganize the order to allow for
        # better binding multiple resources in same filesystem path
        self.bwrap_args.append('bwrap')

        dbus_session_opts: Set[str] = set()
        dbus_system_opts: Set[str] = set()
        seccomp_state: Optional[SeccompState] = None
        # Unshare all
        self.bwrap_args.append('--unshare-all')
        # Die with parent
        self.bwrap_args.append('--die-with-parent')

        if not self.is_shell_debug:
            # Set new session
            self.bwrap_args.append('--new-session')

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

        for service in self.instance_config.iter_services():
            config_iterator = service.__iter__()

            while True:
                try:
                    config = next(config_iterator)
                except StopIteration:
                    break

                # When we need to send something to generator
                if isinstance(config, ServiceWantsHomeBind):
                    config = config_iterator.send(self.home_bind_path)

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
                elif isinstance(config, DbusSessionArgs):
                    dbus_session_opts.add(config.to_args())
                elif isinstance(config, DbusSystemArgs):
                    dbus_system_opts.add(config.to_args())
                elif isinstance(config, SeccompDirective):
                    if seccomp_state is None:
                        seccomp_state = SeccompState()

                    seccomp_state.add_directive(config)
                elif isinstance(config, LaunchArguments):
                    # TODO: implement priority
                    self.executable_args.extend(config.launch_args)
                else:
                    raise TypeError('Unknown bwrap config.')

        if seccomp_state is not None:
            if __debug__:
                seccomp_state.print()

            seccomp_temp_file = seccomp_state.export_to_temp_file()
            seccomp_fd = seccomp_temp_file.fileno()
            self.file_descriptors_to_pass.append(seccomp_fd)
            self.temp_files.append(seccomp_temp_file)
            self.bwrap_args.extend(('--seccomp', str(seccomp_fd)))

        env_dbus_session_addr = 'DBUS_SESSION_BUS_ADDRESS'

        # region dbus
        self.dbus_proxy_args.extend((
            'xdg-dbus-proxy',
            environ[env_dbus_session_addr],
            str(self.dbus_session_socket_path),
        ))

        self.dbus_proxy_args.extend(dbus_session_opts)
        self.dbus_proxy_args.append('--filter')
        if self.is_log_dbus:
            self.dbus_proxy_args.append('--log')

        # Bind session socket inside the sandbox
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

        # System dbus
        self.dbus_proxy_args.extend((
            'unix:path=/run/dbus/system_bus_socket',
            str(self.dbus_system_socket_path),
        ))

        self.dbus_proxy_args.append('--filter')
        if self.is_log_dbus:
            self.dbus_proxy_args.append('--log')

        # Bind twice, in /var and /run
        self.bwrap_args.extend(
            Bind(
                str(self.dbus_system_socket_path),
                '/var/run/dbus/system_bus_socket').to_args()
        )

        self.bwrap_args.extend(
            Bind(
                str(self.dbus_system_socket_path),
                '/run/dbus/system_bus_socket').to_args()
        )
        # endregion dbus

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
        # If the dir exists exception will be raised indicating that
        # instance is already running or did not clean-up properly.
        self.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        # Create helper directory
        self.helper_runtime_dir.mkdir(mode=0o700)

        # Dbus session proxy

        self.dbus_session_socket = socket(AF_UNIX, SOCK_STREAM)
        self.dbus_session_socket.bind(
            str(self.dbus_session_socket_path))

        self.dbus_system_socket = socket(AF_UNIX, SOCK_STREAM)
        self.dbus_system_socket.bind(
            str(self.dbus_system_socket_path))

        # Pylint does not recognize *args for some reason
        # pylint: disable=E1120
        self.dbus_proxy_process = await create_subprocess_exec(
            *self.dbus_proxy_args,
            stdout=(asyncio_pipe
                    if not self.is_shell_debug
                    else asyncio_devnull),
            stderr=asyncio_stdout,
            stdin=asyncio_devnull,
        )

        self.watch_dbus_proxy_task = create_task(
            process_watcher(self.dbus_proxy_process),
            name='dbus proxy',
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

        if self.dbus_proxy_process is not None:
            self.dbus_proxy_process.terminate()
            await self.dbus_proxy_process.wait()

        for t in self.temp_files:
            t.close()

        if self.helper_socket_path.exists():
            self.helper_socket_path.unlink()

        self.helper_runtime_dir.rmdir()

        if self.dbus_session_socket_path.exists():
            self.dbus_session_socket_path.unlink()

        if self.dbus_session_socket is not None:
            self.dbus_session_socket.close()

        if self.dbus_system_socket_path.exists():
            self.dbus_system_socket_path.unlink()

        if self.dbus_system_socket is not None:
            self.dbus_system_socket.close()

        self.runtime_dir.rmdir()


class BubblejailProfile:
    def __init__(
        self,
        dot_desktop_path: Optional[str] = None,
        is_gtk_application: bool = False,
        services:  Optional[ServicesConfDictType] = None,
        description: str = 'No description',
        import_tips: str = 'None',
    ) -> None:
        self.dot_desktop_path = (Path(dot_desktop_path)
                                 if dot_desktop_path is not None else None)
        self.is_gtk_application = is_gtk_application
        self.config = BubblejailInstanceConfig(services)
        self.description = description
        self.import_tips = import_tips


class BubblejailInstanceMetadata:
    def __init__(
        self,
        parent: BubblejailInstance,
        creation_profile_name: Optional[str] = None,
        desktop_entry_name: Optional[str] = None,
    ):
        self.parent = parent
        self.creation_profile_name = creation_profile_name
        self.desktop_entry_name = desktop_entry_name

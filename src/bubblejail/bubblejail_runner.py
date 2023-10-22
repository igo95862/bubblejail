# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2023 igo95862

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
from __future__ import annotations

from asyncio import (
    Future,
    InvalidStateError,
    create_subprocess_exec,
    get_running_loop,
    wait_for,
)
from contextlib import suppress as exc_suppress
from json import load as json_load
from os import O_CLOEXEC, O_NONBLOCK, environ, kill, pipe2
from signal import SIGTERM
from socket import AF_UNIX, socket
from tempfile import TemporaryFile
from traceback import print_exc
from typing import TYPE_CHECKING

from .bubblejail_seccomp import SeccompState
from .bubblejail_utils import BubblejailSettings
from .bwrap_config import (
    Bind,
    BwrapConfigBase,
    DbusSessionArgs,
    DbusSystemArgs,
    FileTransfer,
    LaunchArguments,
    SeccompDirective,
)
from .services import ServiceWantsDbusSessionBind, ServiceWantsHomeBind

if TYPE_CHECKING:
    from asyncio import Task
    from asyncio.subprocess import Process
    from collections.abc import Awaitable, Callable, Iterable, Iterator
    from typing import IO, Any, Type

    from .bubblejail_instance import BubblejailInstance
    from .services import ServiceContainer as BubblejailInstanceConfig


def copy_data_to_temp_file(data: bytes) -> IO[bytes]:
    temp_file = TemporaryFile()
    temp_file.write(data)
    temp_file.seek(0)
    return temp_file


class BubblejailRunner:
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
        self.bwrap_temp_files: list[IO[bytes]] = []
        self.file_descriptors_to_pass: list[int] = []
        # Helper
        self.helper_executable: list[str] = [
            BubblejailSettings.HELPER_PATH_STR]
        self.helper_runtime_dir = parent.path_runtime_helper_dir
        self.helper_socket_path = parent.path_runtime_helper_socket
        self.helper_socket = socket(AF_UNIX)
        self.helper_socket.set_inheritable(True)
        self.helper_socket_fd = self.helper_socket.fileno()
        self.file_descriptors_to_pass.append(self.helper_socket_fd)

        # Args to dbus proxy
        self.dbus_proxy_args: list[str] = []
        self.dbus_proxy_process: Process | None = None

        self.dbus_proxy_pipe_read: int = -1
        self.dbus_proxy_pipe_write: int = -1

        # Dbus session socket
        self.dbus_session_socket_path = parent.path_runtime_dbus_session_socket

        # Dbus system socket
        self.dbus_system_socket_path = parent.path_runtime_dbus_system_socket

        # Args to bwrap
        self.bwrap_options_args: list[str] = []
        self.bwrap_extra_options: list[str] = []
        # Debug mode
        self.is_shell_debug = is_shell_debug
        self.is_log_dbus = is_log_dbus
        # Instance config
        self.instance_config = instance_config

        # Executable args
        self.executable_args: list[str] = []

        # Info fd
        self.info_fd_pipe_read: int = -1
        self.info_fd_pipe_write: int = -1
        self.sandboxed_pid: Future[int] = Future()

        # Tasks
        self.task_post_init: Task[None] | None = None

        # Bubblewrap
        self.bubblewrap_process: Process | None = None
        self.bubblewrap_pid: int | None = None

        self.post_init_hooks: list[Callable[[int], Awaitable[None]]] = []
        self.post_shutdown_hooks: list[Callable[[], Awaitable[None]]] = []

        self.ready_fd_pipe_read: int | None = None
        self.ready_fd_pipe_write: int | None = None

    def genetate_args(self) -> None:
        # TODO: Reorganize the order to allow for
        # better binding multiple resources in same filesystem path

        dbus_session_opts: set[str] = set()
        dbus_system_opts: set[str] = set()
        seccomp_state: SeccompState | None = None
        # Unshare all
        self.bwrap_options_args.append('--unshare-all')
        # Die with parent
        self.bwrap_options_args.append('--die-with-parent')
        # We have our own reaper
        self.bwrap_options_args.append('--as-pid-1')

        if not self.is_shell_debug:
            # Set new session
            self.bwrap_options_args.append('--new-session')

        # Proc
        self.bwrap_options_args.extend(('--proc', '/proc'))
        # Devtmpfs
        self.bwrap_options_args.extend(('--dev', '/dev'))

        # Unset all variables
        self.bwrap_options_args.append('--clearenv')

        # Pass terminal variables if debug shell activated
        if self.is_shell_debug:
            if term_env := environ.get("TERM"):
                self.bwrap_options_args.extend(
                    ("--setenv", "TERM", term_env)
                )

            if colorterm_env := environ.get("COLORTERM"):
                self.bwrap_options_args.extend(
                    ("--setenv", "COLORTERM", colorterm_env)
                )

        for service in self.instance_config.iter_services():
            config_iterator = service.iter_bwrap_options()

            while True:
                try:
                    config = next(config_iterator)
                except StopIteration:
                    break

                # When we need to send something to generator
                if isinstance(config, ServiceWantsHomeBind):
                    config = config_iterator.send(self.home_bind_path)
                elif isinstance(config, ServiceWantsDbusSessionBind):
                    config = config_iterator.send(
                        self.dbus_session_socket_path)

                if isinstance(config, BwrapConfigBase):
                    self.bwrap_options_args.extend(config.to_args())
                elif isinstance(config, FileTransfer):
                    # Copy files
                    temp_f = copy_data_to_temp_file(config.content)
                    self.bwrap_temp_files.append(temp_f)
                    temp_file_descriptor = temp_f.fileno()
                    self.file_descriptors_to_pass.append(
                        temp_file_descriptor)
                    self.bwrap_options_args.extend(
                        (
                            '--ro-bind-data',
                            str(temp_file_descriptor),
                            config.dest,
                        )
                    )
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
            seccomp_temp_file = seccomp_state.export_to_temp_file()
            seccomp_fd = seccomp_temp_file.fileno()
            self.file_descriptors_to_pass.append(seccomp_fd)
            self.bwrap_temp_files.append(seccomp_temp_file)
            self.bwrap_options_args.extend(('--seccomp', str(seccomp_fd)))

        self.post_init_hooks.extend(
            self.instance_config.iter_post_init_hooks()
        )
        self.post_shutdown_hooks.extend(
            self.instance_config.iter_post_shutdown_hooks()
        )

        # region dbus
        # Session dbus
        self.dbus_proxy_args.extend((
            'xdg-dbus-proxy',
            environ['DBUS_SESSION_BUS_ADDRESS'],
            str(self.dbus_session_socket_path),
        ))

        self.dbus_proxy_pipe_read, self.dbus_proxy_pipe_write \
            = pipe2(O_NONBLOCK | O_CLOEXEC)

        self.dbus_proxy_args.append(f"--fd={self.dbus_proxy_pipe_write}")

        self.dbus_proxy_args.extend(dbus_session_opts)
        self.dbus_proxy_args.append('--filter')
        if self.is_log_dbus:
            self.dbus_proxy_args.append('--log')

        # System dbus
        self.dbus_proxy_args.extend((
            'unix:path=/run/dbus/system_bus_socket',
            str(self.dbus_system_socket_path),
        ))

        self.dbus_proxy_args.append('--filter')
        if self.is_log_dbus:
            self.dbus_proxy_args.append('--log')

        # Bind twice, in /var and /run
        self.bwrap_options_args.extend(
            Bind(
                str(self.dbus_system_socket_path),
                '/var/run/dbus/system_bus_socket').to_args()
        )

        self.bwrap_options_args.extend(
            Bind(
                str(self.dbus_system_socket_path),
                '/run/dbus/system_bus_socket').to_args()
        )
        # endregion dbus

        # Info fd pipe
        self.info_fd_pipe_read, self.info_fd_pipe_write = (
            pipe2(O_NONBLOCK | O_CLOEXEC)
        )
        self.file_descriptors_to_pass.append(self.info_fd_pipe_write)
        self.bwrap_options_args.extend(
            ("--info-fd", f"{self.info_fd_pipe_write}"))
        running_loop = get_running_loop()
        running_loop.add_reader(
            self.info_fd_pipe_read,
            self.read_info_fd,
        )

        if self.post_init_hooks:
            self.ready_fd_pipe_read, self.ready_fd_pipe_write = (
                pipe2(O_NONBLOCK | O_CLOEXEC)
            )
            self.file_descriptors_to_pass.append(self.ready_fd_pipe_read)

        self.bwrap_options_args.extend(self.bwrap_extra_options)

    def helper_arguments(self) -> Iterator[str]:
        yield from self.helper_executable
        yield "--helper-socket"
        yield str(self.helper_socket_fd)

        if self.ready_fd_pipe_read:
            yield "--ready-fd"
            yield str(self.ready_fd_pipe_read)

        if self.is_shell_debug:
            yield "--shell"

        yield "--"

    def read_info_fd(self) -> None:
        with open(self.info_fd_pipe_read, closefd=False) as f:
            info_dict = json_load(f)
            self.sandboxed_pid.set_result(info_dict["child-pid"])

    def get_args_file_descriptor(self) -> int:
        options_null = '\0'.join(self.bwrap_options_args)

        args_tempfile = copy_data_to_temp_file(options_null.encode())
        args_tempfile_fileno = args_tempfile.fileno()
        self.file_descriptors_to_pass.append(args_tempfile_fileno)
        self.bwrap_temp_files.append(args_tempfile)

        return args_tempfile_fileno

    async def setup_dbus_proxy(self) -> None:
        running_loop = get_running_loop()
        dbus_proxy_ready_future: Future[bool] = Future()

        def proxy_ready_callback() -> None:
            try:
                with open(self.dbus_proxy_pipe_read, closefd=False) as f:
                    f.read()
            except Exception as e:
                dbus_proxy_ready_future.set_exception(e)
            else:
                dbus_proxy_ready_future.set_result(True)

            running_loop.remove_reader(self.dbus_proxy_pipe_read)

        running_loop.add_reader(
            self.dbus_proxy_pipe_read,
            proxy_ready_callback,
        )

        self.dbus_proxy_process = await create_subprocess_exec(
            *self.dbus_proxy_args,
            pass_fds=[self.dbus_proxy_pipe_write],
        )

        await wait_for(dbus_proxy_ready_future, timeout=1)

        if self.dbus_proxy_process.returncode is not None:
            raise ValueError(
                f"dbus proxy error code: {self.dbus_proxy_process.returncode}")

    async def create_bubblewrap_subprocess(
        self,
        run_args: Iterable[str] | None = None,
    ) -> Process:
        bwrap_args = ['/usr/bin/bwrap']
        # Pass option args file descriptor
        bwrap_args.append('--args')
        bwrap_args.append(str(self.get_args_file_descriptor()))
        bwrap_args.append("--")

        bwrap_args.extend(self.helper_arguments())

        if run_args:
            bwrap_args.extend(run_args)
        else:
            bwrap_args.extend(self.executable_args)

        self.bubblewrap_process = await create_subprocess_exec(
            *bwrap_args,
            pass_fds=self.file_descriptors_to_pass,
        )

        self.bubblewrap_pid = self.bubblewrap_process.pid

        loop = get_running_loop()

        loop.add_signal_handler(SIGTERM, self.sigterm_handler)
        self.task_post_init = loop.create_task(self._run_post_init_hooks())

        await self.task_post_init

        return self.bubblewrap_process

    async def _run_post_init_hooks(self) -> None:
        sandboxed_pid = await self.sandboxed_pid
        if __debug__:
            print(f"Sandboxed PID: {sandboxed_pid}")

        for hook in self.post_init_hooks:
            await hook(sandboxed_pid)

        if self.ready_fd_pipe_read and self.ready_fd_pipe_write:
            with (
                open(self.ready_fd_pipe_read),
                open(self.ready_fd_pipe_write, mode="w") as f
            ):
                f.write("bubblejail-ready")

        with exc_suppress(IndexError):
            while t := self.bwrap_temp_files.pop():
                t.close()

    async def _run_post_shutdown_hooks(self) -> None:
        for hook in self.post_shutdown_hooks:
            try:
                await hook()
            except Exception:
                print("Failed to run post shutdown hook: ", hook)
                print_exc()

    def sigterm_handler(self) -> None:
        try:
            pid_to_kill = self.sandboxed_pid.result()
        except InvalidStateError:
            # Bubblewrap did not finish initializing
            if self.bubblewrap_pid is None:
                return

            pid_to_kill = self.bubblewrap_pid

        print("Terminating PID: ", pid_to_kill)
        kill(pid_to_kill, SIGTERM)
        # No need to wait as the bwrap should terminate when helper exits

    async def __aenter__(self) -> None:
        # Generate args
        self.genetate_args()

        # Create runtime dir
        # If the dir exists exception will be raised indicating that
        # instance is already running or did not clean-up properly.
        self.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        # Create helper directory
        self.helper_runtime_dir.mkdir(mode=0o700)
        self.helper_socket.bind(bytes(self.helper_socket_path))

        await self.setup_dbus_proxy()

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc: BaseException,
        traceback: Any,  # ???: What type is traceback
    ) -> None:
        # Cleanup
        try:
            if self.bubblewrap_process is not None:
                self.bubblewrap_process.terminate()
                await wait_for(self.bubblewrap_process.wait(), timeout=3)
        except ProcessLookupError:
            ...

        await self._run_post_shutdown_hooks()

        try:
            if self.dbus_proxy_process is not None:
                self.dbus_proxy_process.terminate()
                await wait_for(self.dbus_proxy_process.wait(), timeout=3)
        except ProcessLookupError:
            ...

        try:
            self.helper_socket_path.unlink()
        except FileNotFoundError:
            ...

        try:
            self.helper_runtime_dir.rmdir()
        except FileNotFoundError:
            ...
        except OSError:
            ...

        try:
            self.dbus_session_socket_path.unlink()
        except FileNotFoundError:
            ...

        try:
            self.dbus_system_socket_path.unlink()
        except FileNotFoundError:
            ...

        try:
            self.runtime_dir.rmdir()
        except FileNotFoundError:
            ...
        except OSError:
            ...

    def __del__(self) -> None:
        try:
            self.helper_socket.close()
        except OSError:
            ...

        for t in self.bwrap_temp_files:
            t.close()

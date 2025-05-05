# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2023 igo95862
from __future__ import annotations

from asyncio import Future, create_subprocess_exec, get_running_loop, wait_for
from contextlib import asynccontextmanager, contextmanager
from contextlib import suppress as exc_suppress
from io import StringIO
from json import loads as json_loads
from os import O_CLOEXEC, O_NONBLOCK
from os import close as close_fd
from os import environ, kill, pipe2
from signal import SIGTERM
from socket import AF_UNIX, socket
from sys import stderr
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
from .dbus_proxy import XdgDbusProxy
from .services import ServiceWantsDbusSessionBind, ServiceWantsHomeBind

if TYPE_CHECKING:
    from asyncio import Task
    from asyncio.subprocess import Process
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Iterator
    from contextlib import AsyncExitStack
    from typing import IO

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
        self.helper_executable: list[str] = [BubblejailSettings.HELPER_PATH_STR]
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

        # D-Bus proxy
        self.dbus_session_socket_path = parent.path_runtime_dbus_session_socket
        self.dbus_system_socket_path = parent.path_runtime_dbus_system_socket
        self.dbus_proxy = XdgDbusProxy(
            self.dbus_session_socket_path, self.dbus_system_socket_path, is_log_dbus
        )

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
        self.sandboxed_pid: int | None = None

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

        seccomp_state: SeccompState | None = None
        # Unshare all
        self.bwrap_options_args.append("--unshare-all")
        # Die with parent
        self.bwrap_options_args.append("--die-with-parent")
        # We have our own reaper
        self.bwrap_options_args.append("--as-pid-1")

        if not self.is_shell_debug:
            # Set new session
            self.bwrap_options_args.append("--new-session")

        # Proc
        self.bwrap_options_args.extend(("--proc", "/proc"))
        # Devtmpfs
        self.bwrap_options_args.extend(("--dev", "/dev"))

        # Unset all variables
        self.bwrap_options_args.append("--clearenv")

        # Pass terminal variables if debug shell activated
        if self.is_shell_debug:
            if term_env := environ.get("TERM"):
                self.bwrap_options_args.extend(("--setenv", "TERM", term_env))

            if colorterm_env := environ.get("COLORTERM"):
                self.bwrap_options_args.extend(("--setenv", "COLORTERM", colorterm_env))

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
                    config = config_iterator.send(self.dbus_session_socket_path)

                if isinstance(config, BwrapConfigBase):
                    self.bwrap_options_args.extend(config.to_args())
                elif isinstance(config, FileTransfer):
                    # Copy files
                    temp_f = copy_data_to_temp_file(config.content)
                    self.bwrap_temp_files.append(temp_f)
                    temp_file_descriptor = temp_f.fileno()
                    self.file_descriptors_to_pass.append(temp_file_descriptor)
                    self.bwrap_options_args.extend(
                        (
                            "--ro-bind-data",
                            str(temp_file_descriptor),
                            config.dest,
                        )
                    )
                elif isinstance(config, (DbusSessionArgs, DbusSystemArgs)):
                    self.dbus_proxy.add_dbus_rule(config)
                elif isinstance(config, SeccompDirective):
                    if seccomp_state is None:
                        seccomp_state = SeccompState()

                    seccomp_state.add_directive(config)
                elif isinstance(config, LaunchArguments):
                    # TODO: implement priority
                    self.executable_args.extend(config.launch_args)
                else:
                    raise TypeError("Unknown bwrap config.")

        if seccomp_state is not None:
            seccomp_temp_file = seccomp_state.export_to_temp_file()
            seccomp_fd = seccomp_temp_file.fileno()
            self.file_descriptors_to_pass.append(seccomp_fd)
            self.bwrap_temp_files.append(seccomp_temp_file)
            self.bwrap_options_args.extend(("--seccomp", str(seccomp_fd)))

        self.post_init_hooks.extend(self.instance_config.iter_post_init_hooks())
        self.post_shutdown_hooks.extend(self.instance_config.iter_post_shutdown_hooks())

        # Bind twice, in /var and /run
        self.bwrap_options_args.extend(
            Bind(
                str(self.dbus_system_socket_path), "/var/run/dbus/system_bus_socket"
            ).to_args()
        )

        self.bwrap_options_args.extend(
            Bind(
                str(self.dbus_system_socket_path), "/run/dbus/system_bus_socket"
            ).to_args()
        )

        # Info fd pipe
        self.info_fd_pipe_read, self.info_fd_pipe_write = pipe2(O_NONBLOCK | O_CLOEXEC)
        self.file_descriptors_to_pass.append(self.info_fd_pipe_write)
        self.bwrap_options_args.extend(("--info-fd", f"{self.info_fd_pipe_write}"))

        if self.post_init_hooks:
            self.ready_fd_pipe_read, self.ready_fd_pipe_write = pipe2(
                O_NONBLOCK | O_CLOEXEC
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

    async def read_info_fd(self) -> None:
        close_fd(self.info_fd_pipe_write)

        loop = get_running_loop()

        info_json_future: Future[None] = loop.create_future()
        info_json_buffer = StringIO()

        with open(self.info_fd_pipe_read) as f:

            def info_json_reader() -> None:
                json_fragment = f.read()
                if json_fragment:
                    info_json_buffer.write(json_fragment)
                else:
                    # On EOF empty string is returned
                    loop.remove_reader(self.info_fd_pipe_read)
                    info_json_future.set_result(None)

            loop.add_reader(self.info_fd_pipe_read, info_json_reader)
            await info_json_future

        info_dict = json_loads(info_json_buffer.getvalue())
        self.sandboxed_pid = info_dict["child-pid"]

    def get_args_file_descriptor(self) -> int:
        options_null = "\0".join(self.bwrap_options_args)

        args_tempfile = copy_data_to_temp_file(options_null.encode())
        args_tempfile_fileno = args_tempfile.fileno()
        self.file_descriptors_to_pass.append(args_tempfile_fileno)
        self.bwrap_temp_files.append(args_tempfile)

        return args_tempfile_fileno

    async def _run_post_init_hooks(self) -> None:
        sandboxed_pid = self.sandboxed_pid
        if sandboxed_pid is None:
            raise RuntimeError("Sandboxed PID not acquired!")

        print(f"Sandboxed PID: {sandboxed_pid}", file=stderr)

        for hook in self.post_init_hooks:
            await hook(sandboxed_pid)

        if self.ready_fd_pipe_read and self.ready_fd_pipe_write:
            with (
                open(self.ready_fd_pipe_read),
                open(self.ready_fd_pipe_write, mode="w") as f,
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
                print("Failed to run post shutdown hook: ", hook, file=stderr)
                print_exc(file=stderr)

    def sigterm_handler(self) -> None:
        if self.sandboxed_pid is not None:
            pid_to_kill = self.sandboxed_pid
        else:
            if self.bubblewrap_pid is None:
                return

            pid_to_kill = self.bubblewrap_pid

        print("Terminating PID: ", pid_to_kill, file=stderr)
        kill(pid_to_kill, SIGTERM)
        # No need to wait as the bwrap should terminate when helper exits

    @contextmanager
    def setup_runtime_dir(self) -> Iterator[None]:
        try:
            # Create runtime dir
            # If the dir exists exception will be raised indicating that
            # instance is already running or did not clean-up properly.
            self.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
            yield None
        finally:
            with exc_suppress(FileNotFoundError, OSError):
                self.runtime_dir.rmdir()

    @contextmanager
    def setup_helper_runtime_dir(self) -> Iterator[None]:
        try:
            # Create helper directory
            self.helper_runtime_dir.mkdir(mode=0o700)
            yield None
        finally:
            with exc_suppress(FileNotFoundError, OSError):
                self.helper_runtime_dir.rmdir()

    @contextmanager
    def setup_helper_socket(self) -> Iterator[None]:
        try:
            self.helper_socket.bind(bytes(self.helper_socket_path))
            yield None
        finally:
            with exc_suppress(FileNotFoundError):
                self.helper_socket_path.unlink()

    @asynccontextmanager
    async def setup_bubblewrap_subprocess(
        self,
        run_args: Iterable[str] | None = None,
    ) -> AsyncIterator[Process]:
        bwrap_args = ["/usr/bin/bwrap"]
        # Pass option args file descriptor
        bwrap_args.append("--args")
        bwrap_args.append(str(self.get_args_file_descriptor()))
        bwrap_args.append("--")

        bwrap_args.extend(self.helper_arguments())

        if run_args:
            bwrap_args.extend(run_args)
        else:
            bwrap_args.extend(self.executable_args)

        try:
            self.bubblewrap_process = await create_subprocess_exec(
                *bwrap_args,
                pass_fds=self.file_descriptors_to_pass,
            )

            self.bubblewrap_pid = self.bubblewrap_process.pid

            await wait_for(self.read_info_fd(), timeout=3)

            loop = get_running_loop()

            loop.add_signal_handler(SIGTERM, self.sigterm_handler)
            self.task_post_init = loop.create_task(self._run_post_init_hooks())

            await self.task_post_init

            yield self.bubblewrap_process
        finally:
            with exc_suppress(ProcessLookupError, TimeoutError):
                if self.bubblewrap_process is not None:
                    self.bubblewrap_process.terminate()
                    await wait_for(self.bubblewrap_process.wait(), timeout=3)

    async def setup_runtime(
        self,
        exit_stack: AsyncExitStack,
        run_args: Iterable[str] | None = None,
    ) -> Process:
        self.genetate_args()
        exit_stack.enter_context(self.setup_runtime_dir())
        exit_stack.enter_context(self.setup_helper_runtime_dir())
        exit_stack.enter_context(self.setup_helper_socket())
        await exit_stack.enter_async_context(self.dbus_proxy.exit_stack)
        await self.dbus_proxy.start()
        exit_stack.push_async_callback(self._run_post_shutdown_hooks)
        return await exit_stack.enter_async_context(
            self.setup_bubblewrap_subprocess(run_args)
        )

    def __del__(self) -> None:
        try:
            self.helper_socket.close()
        except OSError:
            ...

        for t in self.bwrap_temp_files:
            t.close()

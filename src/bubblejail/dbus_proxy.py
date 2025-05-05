# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 igo95862
from __future__ import annotations

from asyncio import create_subprocess_exec, wait_for
from contextlib import AsyncExitStack, suppress
from os import O_CLOEXEC, O_NONBLOCK, environ, pipe2
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING

from .bwrap_config import DbusSessionArgs, DbusSystemArgs
from .utils import aread_once

if TYPE_CHECKING:
    from asyncio.subprocess import Process as AsyncioProcess
    from typing import BinaryIO


class XdgDbusProxy:
    def __init__(
        self,
        dbus_session_socket_path: Path,
        dbus_system_socket_path: Path,
        log_dbus: bool,
    ):
        self.log_dbus = log_dbus
        self.dbus_session_socket_path = dbus_session_socket_path
        self.dbus_system_socket_path = dbus_system_socket_path
        self.dbus_session_opts: list[str] = []
        self.dbus_system_opts: list[str] = []
        self.exit_stack = AsyncExitStack()

        self.dbus_proxy_process: AsyncioProcess | None = None

    def add_dbus_rule(self, rule: DbusSessionArgs | DbusSystemArgs) -> None:
        match rule:
            case DbusSessionArgs():
                self.dbus_session_opts.append(rule.to_args())
            case DbusSystemArgs():
                self.dbus_system_opts.append(rule.to_args())
            case _:
                raise TypeError(f"Expected D-Bus rule, got {rule!r}")

    def generate_args(self, ready_pipe: BinaryIO) -> list[str]:
        dbus_proxy_binary = which("xdg-dbus-proxy")
        if dbus_proxy_binary is None:
            raise RuntimeError("xdg-dbus-proxy not found")

        dbus_proxy_args: list[str] = [dbus_proxy_binary, f"--fd={ready_pipe.fileno()}"]

        # D-Bus session
        dbus_proxy_args.append(environ["DBUS_SESSION_BUS_ADDRESS"])
        dbus_proxy_args.append(str(self.dbus_session_socket_path))
        dbus_proxy_args.extend(self.dbus_session_opts)
        dbus_proxy_args.append("--filter")
        if self.log_dbus:
            dbus_proxy_args.append("--log")

        # D-Bus system
        dbus_proxy_args.append("unix:path=/run/dbus/system_bus_socket")
        dbus_proxy_args.append(str(self.dbus_system_socket_path))
        dbus_proxy_args.extend(self.dbus_system_opts)
        dbus_proxy_args.append("--filter")
        if self.log_dbus:
            dbus_proxy_args.append("--log")

        return dbus_proxy_args

    async def terminate_dbus_proxy(self, read_pipe: BinaryIO) -> None:
        if self.dbus_proxy_process is None:
            return

        read_pipe.close()
        with suppress(TimeoutError):
            await wait_for(self.dbus_proxy_process.wait(), timeout=3)
            return

        self.dbus_proxy_process.terminate()
        with suppress(TimeoutError):
            await wait_for(self.dbus_proxy_process.wait(), timeout=3)
            return

        self.dbus_proxy_process.kill()
        with suppress(TimeoutError):
            await wait_for(self.dbus_proxy_process.wait(), timeout=3)

    def unlink_sockets(self) -> None:
        with suppress(FileNotFoundError):
            self.dbus_session_socket_path.unlink()

        with suppress(FileNotFoundError):
            self.dbus_system_socket_path.unlink()

    async def start(self) -> None:
        read_pipe_fd, write_pipe_fd = pipe2(O_NONBLOCK | O_CLOEXEC)
        read_pipe = open(read_pipe_fd, mode="rb")
        self.exit_stack.callback(read_pipe.close)
        write_pipe = open(write_pipe_fd, mode="wb")
        self.exit_stack.callback(write_pipe.close)

        dbus_proxy_args = self.generate_args(write_pipe)
        self.dbus_proxy_process = await create_subprocess_exec(
            *dbus_proxy_args,
            pass_fds=[write_pipe.fileno()],
        )
        await aread_once(read_pipe)
        write_pipe.close()
        if self.dbus_proxy_process.returncode is not None:
            raise RuntimeError(
                "D-Bus proxy exited with code: ", self.dbus_proxy_process.returncode
            )
        self.exit_stack.callback(self.unlink_sockets)
        self.exit_stack.push_async_callback(self.terminate_dbus_proxy, read_pipe)

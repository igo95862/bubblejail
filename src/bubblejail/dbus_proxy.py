# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 igo95862
from __future__ import annotations

from asyncio import create_subprocess_exec, get_running_loop, wait_for
from contextlib import AsyncExitStack, suppress
from dataclasses import dataclass
from enum import StrEnum
from os import O_CLOEXEC, O_NONBLOCK, environ, pipe2
from pathlib import Path
from shutil import which
from subprocess import PIPE
from sys import stderr
from typing import TYPE_CHECKING

from .bwrap_config import DbusSessionArgs, DbusSystemArgs
from .utils import aread_once

if TYPE_CHECKING:
    from asyncio import StreamReader, Task
    from asyncio.subprocess import Process as AsyncioProcess
    from typing import BinaryIO


class DBusProxyLogParser:
    @dataclass
    class DBusCall:
        service_name: str
        interface_member_name: str
        object_path: str

    @dataclass
    class DBusFiltering:
        dbus_name: str
        current_policy: str
        required_policy: str

    def __init__(self) -> None:
        self.wants_own_names: set[str] = set()
        self.wants_own_first_name: str | None = None
        self.wants_talk_to: set[str] = set()
        self.previous_call_line: DBusProxyLogParser.DBusCall | None = None

        import re

        self.filtering_regex = re.compile(
            r"^Filtering message due to arg0 (?P<dbus_name>[\w.]+), "
            r"policy: (?P<current_policy>\d) \(required (?P<required_policy>\d)\)"
        )
        self.call_regex = re.compile(
            r"^C\d+: -> (?P<service_name>[\w.]+) call "
            r"(?P<interface_member_name>[\w.]+) at (?P<object_path>[\w/]+)"
        )

    def process_log_line(self, line: str) -> None:
        previous_call_line = self.previous_call_line
        self.previous_call_line = None

        if filtering_match := self.filtering_regex.match(line):
            filtering_event = DBusProxyLogParser.DBusFiltering(
                **filtering_match.groupdict()
            )

            match previous_call_line:
                case None:
                    print(
                        "Found D-Bus filtering message but no previous line to analyze",
                        file=stderr,
                    )
                    return
                case DBusProxyLogParser.DBusCall(
                    service_name="org.freedesktop.DBus",
                    interface_member_name="org.freedesktop.DBus.RequestName",
                ):
                    if filtering_event.required_policy == "3":
                        print(
                            f"D-Bus: Blocked from owning name {filtering_event.dbus_name!r}",
                            file=stderr,
                        )
                        self.wants_own_names.add(filtering_event.dbus_name)
                        if self.wants_own_first_name is None:
                            self.wants_own_first_name = filtering_event.dbus_name
                case DBusProxyLogParser.DBusCall(
                    service_name="org.freedesktop.DBus",
                    interface_member_name="org.freedesktop.DBus.GetNameOwner",
                ) | DBusProxyLogParser.DBusCall(
                    service_name="org.freedesktop.DBus",
                    interface_member_name="org.freedesktop.DBus.StartServiceByName",
                ):
                    print(
                        f"D-Bus: Blocked from inquiring about {filtering_event.dbus_name!r} service",
                        file=stderr,
                    )
                    self.wants_talk_to.add(filtering_event.dbus_name)
        elif call_match := self.call_regex.match(line):
            self.previous_call_line = DBusProxyLogParser.DBusCall(
                **call_match.groupdict()
            )
        elif line.startswith("*HIDDEN*") and previous_call_line is not None:
            print(
                "D-Bus: Blocked from calling\n"
                f"    Service name: {previous_call_line.service_name!r}\n"
                f"    Object path: {previous_call_line.object_path!r}\n"
                f"    Interface.Member: {previous_call_line.interface_member_name!r}",
                file=stderr,
            )
            self.wants_talk_to.add(previous_call_line.service_name)


class DBusLogEnum(StrEnum):
    NONE = "none"
    RAW = "raw"
    PARSE = "parse"


class XdgDbusProxy:
    def __init__(
        self,
        dbus_session_socket_path: Path,
        dbus_system_socket_path: Path,
        log_dbus: DBusLogEnum,
    ):
        self.log_dbus = log_dbus
        self.dbus_session_socket_path = dbus_session_socket_path
        self.dbus_system_socket_path = dbus_system_socket_path
        self.dbus_session_opts: list[str] = []
        self.dbus_system_opts: list[str] = []
        self.exit_stack = AsyncExitStack()

        self.dbus_proxy_process: AsyncioProcess | None = None
        self.dbus_parser: DBusProxyLogParser | None = None

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
        if self.log_dbus != DBusLogEnum.NONE:
            dbus_proxy_args.append("--log")

        # D-Bus system
        dbus_proxy_args.append("unix:path=/run/dbus/system_bus_socket")
        dbus_proxy_args.append(str(self.dbus_system_socket_path))
        dbus_proxy_args.extend(self.dbus_system_opts)
        dbus_proxy_args.append("--filter")
        if self.log_dbus != DBusLogEnum.NONE:
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
            stdout=PIPE if self.log_dbus == DBusLogEnum.PARSE else None,
        )
        await aread_once(read_pipe)
        write_pipe.close()
        if self.dbus_proxy_process.returncode is not None:
            raise RuntimeError(
                "D-Bus proxy exited with code: ", self.dbus_proxy_process.returncode
            )
        self.exit_stack.callback(self.unlink_sockets)
        self.exit_stack.push_async_callback(self.terminate_dbus_proxy, read_pipe)

        if self.log_dbus == DBusLogEnum.PARSE:
            dbus_parser = DBusProxyLogParser()
            loop = get_running_loop()
            read_logs_task = loop.create_task(
                self.read_proxy_logs(dbus_parser, self.dbus_proxy_process.stdout)
            )
            self.exit_stack.callback(read_logs_task.cancel)
            read_logs_task.add_done_callback(self.check_parser_exc)

    def check_parser_exc(self, parser_task: Task[None]) -> None:
        if parser_task.cancelled():
            return

        if exc := parser_task.exception():
            print(
                "Parser failed with exception:",
                exc,
                file=stderr,
            )

    async def read_proxy_logs(
        self,
        dbus_parser: DBusProxyLogParser,
        stream: StreamReader | None,
    ) -> None:
        if stream is None:
            return

        while line := await stream.readline():
            dbus_parser.process_log_line(line.decode("utf-8"))

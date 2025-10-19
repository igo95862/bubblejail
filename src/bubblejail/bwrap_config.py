# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2022 igo95862
from __future__ import annotations

from collections.abc import Generator
from os import environ
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    Pathlike = str | Path


class BwrapConfigBase:
    __slots__ = ()
    arg_word: str

    def to_args(self) -> Generator[str, None, None]:
        yield self.arg_word


class ShareNetwork(BwrapConfigBase):
    __slots__ = ()
    arg_word = "--share-net"


class BwrapOptionWithPermissions(BwrapConfigBase):
    __slots__ = ("permissions",)

    def __init__(self, permissions: int | None = None):
        super().__init__()
        self.permissions = permissions

    def to_args(self) -> Generator[str, None, None]:
        if self.permissions is not None:
            yield "--perms"
            yield f"{self.permissions:04o}"

        yield from super().to_args()


class DirCreate(BwrapOptionWithPermissions):
    __slots__ = ("dest",)
    arg_word = "--dir"

    def __init__(self, dest: Pathlike, permissions: int | None = None):
        super().__init__(permissions)
        self.dest = str(dest)

    def to_args(self) -> Generator[str, None, None]:
        yield from super().to_args()
        yield self.dest


class Symlink(BwrapConfigBase):
    __slots__ = ("source", "dest")
    arg_word = "--symlink"

    def __init__(self, source: Pathlike, dest: Pathlike):
        super().__init__()
        self.source = str(source)
        self.dest = str(dest)

    def to_args(self) -> Generator[str, None, None]:
        yield from super().to_args()
        yield self.source
        yield self.dest


class EnvironVar(BwrapConfigBase):
    __slots__ = ("var_name", "var_value")
    arg_word = "--setenv"

    def __init__(self, var_name: str, var_value: str | None = None):
        super().__init__()
        self.var_name = var_name
        self.var_value = var_value

    def to_args(self) -> Generator[str, None, None]:
        yield from super().to_args()

        yield self.var_name
        yield (self.var_value if self.var_value is not None else environ[self.var_name])


class ReadOnlyBind(BwrapConfigBase):
    __slots__ = ("source", "dest")
    arg_word = "--ro-bind"

    def __init__(self, source: Pathlike, dest: Pathlike | None = None):
        super().__init__()
        self.source = str(source)
        self.dest = str(dest) if dest is not None else str(source)

    def to_args(self) -> Generator[str, None, None]:
        yield from super().to_args()

        yield self.source
        yield self.dest


class ReadOnlyBindTry(ReadOnlyBind):
    __slots__ = ()
    arg_word = "--ro-bind-try"


class Bind(ReadOnlyBind):
    __slots__ = ()
    arg_word = "--bind"


class BindTry(ReadOnlyBind):
    __slots__ = ()
    arg_word = "--bind-try"


class DevBind(ReadOnlyBind):
    __slots__ = ()
    arg_word = "--dev-bind"


class DevBindTry(ReadOnlyBind):
    __slots__ = ()
    arg_word = "--dev-bind-try"


class ChangeDir(BwrapConfigBase):
    __slots__ = ("dest",)
    arg_word = "--chdir"

    def __init__(self, dest: Pathlike):
        super().__init__()
        self.dest = str(dest)

    def to_args(self) -> Generator[str, None, None]:
        yield from super().to_args()
        yield self.dest


class BwrapRawArgs(BwrapConfigBase):
    __slots__ = ("raw_args",)
    arg_word = ""

    def __init__(self, raw_args: list[str]):
        super().__init__()
        self.raw_args = raw_args

    def to_args(self) -> Generator[str, None, None]:
        yield from self.raw_args


class FileTransfer:
    __slots__ = ("content", "dest")

    def __init__(self, content: bytes, dest: Pathlike):
        self.content = content
        self.dest = str(dest)


class DbusCommon:
    __slots__ = ("bus_name",)
    arg_word: str = "ERROR"

    def __init__(self, bus_name: str):
        self.bus_name = bus_name

    def to_args(self) -> str:
        return f"{self.arg_word}={self.bus_name}"


class DbusSessionArgs(DbusCommon):
    __slots__ = ()


class DbusSystemArgs(DbusCommon):
    __slots__ = ()


class DbusSessionTalkTo(DbusSessionArgs):
    __slots__ = ()
    arg_word = "--talk"


class DbusSessionOwn(DbusSessionArgs):
    __slots__ = ()
    arg_word = "--own"


class DbusSessionSee(DbusSessionArgs):
    __slots__ = ()
    arg_word = "--see"


class DbusSessionRule(DbusSessionArgs):
    __slots__ = ("interface_name", "object_path")

    def __init__(
        self,
        bus_name: str,
        interface_name: str = "*",
        object_path: str = "/*",
    ):
        super().__init__(bus_name)
        self.interface_name = interface_name
        self.object_path = object_path

    def to_args(self) -> str:
        return (
            f"{self.arg_word}={self.bus_name}="
            f"{self.interface_name}@{self.object_path}"
        )


class DbusSessionCall(DbusSessionRule):
    __slots__ = ()
    arg_word = "--call"


class DbusSessionBroadcast(DbusSessionRule):
    __slots__ = ()
    arg_word = "--broadcast"


class DbusSessionRawArg(DbusSessionArgs):
    __slots__ = ()

    def to_args(self) -> str:
        return self.bus_name


class DbusSystemRawArg(DbusSystemArgs):
    __slots__ = ()

    def to_args(self) -> str:
        return self.bus_name


class SeccompDirective:
    __slots__ = ()


class SeccompSyscallErrno(SeccompDirective):
    __slots__ = ("syscall_name", "errno", "skip_on_not_exists")

    def __init__(
        self,
        syscall_name: str,
        errno: int,
        skip_on_not_exists: bool = False,
    ):
        self.syscall_name = syscall_name
        self.errno = errno
        self.skip_on_not_exists = skip_on_not_exists


class LaunchArguments:
    __slots__ = ("launch_args", "priority")

    def __init__(
        self,
        launch_args: list[str],
        priority: int = 0,
    ) -> None:
        self.launch_args = launch_args
        self.priority = priority

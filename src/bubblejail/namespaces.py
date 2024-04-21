# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
from __future__ import annotations

from ctypes import CDLL, c_int, c_long
from ctypes.util import find_library
from fcntl import ioctl
from os import O_CLOEXEC, O_RDONLY
from os import close as close_fd
from os import open as open_fd
from typing import TYPE_CHECKING

from .namespaces_constants import NamespacesConstants

if TYPE_CHECKING:
    from typing import Type, TypeVar

    TNamespace = TypeVar("TNamespace", bound="Namespace")

libc = CDLL(find_library("c"))

setns = libc.syscall
setns.argtypes = [c_long, c_int, c_int]


class Namespace:
    PROC_NAME = ""

    def __init__(self, file_descriptor: int):
        self._fd = file_descriptor

    def __del__(self) -> None:
        close_fd(self._fd)

    def setns(self) -> None:
        setns(NamespacesConstants.SYSCALL_SETNS, self._fd, 0)

    @classmethod
    def from_pid(cls: Type[TNamespace], pid: int) -> TNamespace:
        ns_fd = open_fd(
            f"/proc/{pid}/ns/{cls.PROC_NAME}", O_RDONLY | O_CLOEXEC
        )
        return cls(ns_fd)

    def get_user_ns(self) -> UserNamespace:
        parent_user_fd = ioctl(self._fd, NamespacesConstants.NS_GET_USERNS)
        return UserNamespace(parent_user_fd)


class UserNamespace(Namespace):
    PROC_NAME = "user"


class NetworkNamespace(Namespace):
    PROC_NAME = "net"

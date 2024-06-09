# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2022 igo95862
from __future__ import annotations

from ctypes import CDLL, c_char_p, c_int, c_uint, c_uint32, c_void_p
from ctypes.util import find_library
from platform import machine
from tempfile import TemporaryFile
from typing import TYPE_CHECKING

from .bwrap_config import SeccompDirective, SeccompSyscallErrno
from .exceptions import BubblejailLibseccompError, LibseccompSyscallResolutionError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import IO, Any


SCMP_ACT_ALLOW = c_uint(0x7FFF0000)

ARCH_X86 = c_uint32(3 | 0x40000000)


def get_scmp_act_errno(error_code: int) -> c_uint32:
    return c_uint32(0x00050000 | (error_code & 0x0000FFFF))


class Libseccomp:
    @staticmethod
    def check_libseccomp_ptr(
        result: int | None,
        func: Any,
        arguments: tuple[Any, ...],
    ) -> int:
        if result is None:
            raise BubblejailLibseccompError(
                f"Libseccomp null pointer " f"when calling {func.__name__}."
            )

        return result

    @staticmethod
    def check_syscall_resolve(
        result: int,
        func: Any,
        arguments: tuple[c_char_p],
    ) -> int:

        if result < 0:

            if (syscall_bytes := arguments[0].value) is None:
                syscall_name = "NULL"
            else:
                syscall_name = syscall_bytes.decode("utf-8")

            raise LibseccompSyscallResolutionError(
                f"Failed to resolve syscall {syscall_name}."
            )

        return result

    @staticmethod
    def check_libseccomp_int(
        result: int,
        func: Any,
        arguments: tuple[Any, ...],
    ) -> int:
        if result < 0:
            raise BubblejailLibseccompError(
                f"Libseccomp returned error {result} " f"when calling {func.__name__}."
            )

        return result

    def __init__(self) -> None:
        libseccomp = CDLL(find_library("seccomp"))
        self.libseccomp = libseccomp

        # HACK: mypy is not smart enough to realize that
        # restype affects the function passed to errcheck

        seccomp_init = libseccomp.seccomp_init
        seccomp_init.argtypes = (c_uint,)
        seccomp_init.restype = c_void_p
        seccomp_init.errcheck = self.check_libseccomp_ptr  # type: ignore
        self.init: Callable[[c_uint], c_void_p] = seccomp_init

        seccomp_load = libseccomp.seccomp_load
        seccomp_load.argtypes = (c_void_p,)
        seccomp_load.restype = c_int
        seccomp_load.errcheck = self.check_libseccomp_int  # type: ignore
        self.load: Callable[[c_void_p], c_int] = seccomp_load

        seccomp_syscall_resolve_name = libseccomp.seccomp_syscall_resolve_name
        seccomp_syscall_resolve_name.argtypes = (c_char_p,)
        seccomp_syscall_resolve_name.restype = c_int
        seccomp_syscall_resolve_name.errcheck = (
            self.check_syscall_resolve  # type: ignore
        )
        self.syscall_resolve_name: Callable[[c_char_p], c_int] = (
            seccomp_syscall_resolve_name
        )

        seccomp_rule_add = libseccomp.seccomp_rule_add
        seccomp_rule_add.argtypes = (c_void_p, c_uint32, c_int, c_uint)
        seccomp_rule_add.restype = c_int
        seccomp_rule_add.errcheck = self.check_libseccomp_int  # type: ignore
        self.rule_add: Callable[[c_void_p, c_uint32, c_int, c_uint], c_int] = (
            seccomp_rule_add
        )

        seccomp_export_pfc = libseccomp.seccomp_export_pfc
        seccomp_export_pfc.argtypes = (c_void_p, c_int)
        seccomp_export_pfc.restype = c_int
        seccomp_export_pfc.errcheck = self.check_libseccomp_int  # type: ignore
        self.export_pfc: Callable[[c_void_p, c_int], c_int] = seccomp_export_pfc

        seccomp_export_bpf = libseccomp.seccomp_export_bpf
        seccomp_export_bpf.argtypes = (c_void_p, c_int)
        seccomp_export_bpf.restype = c_int
        seccomp_export_bpf.errcheck = self.check_libseccomp_int  # type: ignore
        self.export_bpf: Callable[[c_void_p, c_int], c_int] = seccomp_export_bpf

        seccomp_arch_add = libseccomp.seccomp_arch_add
        seccomp_arch_add.argtypes = (c_void_p, c_uint32)
        seccomp_arch_add.restype = c_int
        seccomp_arch_add.errcheck = self.check_libseccomp_int  # type: ignore
        self.arch_add: Callable[[c_void_p, c_uint32], c_int] = seccomp_arch_add


class SeccompState:

    def __init__(self) -> None:
        self.libseccomp = Libseccomp()

        self._seccomp_ruleset_ptr = self.libseccomp.init(SCMP_ACT_ALLOW)

        if machine() == "x86_64":
            self.libseccomp.arch_add(self._seccomp_ruleset_ptr, ARCH_X86)

        # TODO: Add armv7 on aarch64 systems

    def filter_syscall(self, syscall_name: str, error_number: int) -> None:
        resolved_syscall_int = self.libseccomp.syscall_resolve_name(
            c_char_p(syscall_name.encode())
        )

        self.libseccomp.rule_add(
            self._seccomp_ruleset_ptr,
            get_scmp_act_errno(error_number),
            resolved_syscall_int,
            c_uint(0),
        )

    def add_directive(self, directive: SeccompDirective) -> None:
        match directive:
            case SeccompSyscallErrno(
                syscall_name=syscall_name,
                errno=errno,
                skip_on_not_exists=skip_on_not_exists,
            ):
                try:
                    self.filter_syscall(syscall_name, errno)
                except LibseccompSyscallResolutionError:
                    if not skip_on_not_exists:
                        raise
            case _:
                raise TypeError("Unknown seccomp directive.")

    def load(self) -> None:
        self.libseccomp.load(self._seccomp_ruleset_ptr)

    def export_to_temp_file(self) -> IO[bytes]:
        t = TemporaryFile()
        self.libseccomp.export_bpf(
            self._seccomp_ruleset_ptr,
            c_int(t.fileno()),
        )
        t.seek(0)
        return t

    def print(self) -> None:
        self.libseccomp.export_pfc(
            self._seccomp_ruleset_ptr,
            c_int(0),
        )

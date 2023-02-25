# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019-2022 igo95862

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

from ctypes import CDLL, c_char_p, c_int, c_uint, c_uint32, c_void_p
from ctypes.util import find_library
from platform import machine
from tempfile import TemporaryFile
from typing import IO, Callable

from .bwrap_config import SeccompDirective, SeccompSyscallErrno

SCMP_ACT_ALLOW = c_uint(0x7fff0000)

ARCH_X86 = c_uint32(3 | 0x40000000)


def get_scmp_act_errno(error_code: int) -> c_uint32:
    return c_uint32(0x00050000 | (error_code & 0x0000ffff))


class Libseccomp:
    def __init__(self) -> None:
        libseccomp = CDLL(find_library('seccomp'))
        self.libseccomp = libseccomp

        seccomp_init = libseccomp.seccomp_init
        seccomp_init.argtypes = (c_uint, )
        seccomp_init.restype = c_void_p
        self.init: Callable[[c_uint], c_void_p] = (
            seccomp_init
        )

        seccomp_load = libseccomp.seccomp_load
        seccomp_load.argtypes = (c_void_p, )
        seccomp_load.restype = c_int
        self.load: Callable[[c_void_p], c_int] = (
            seccomp_load
        )

        seccomp_syscall_resolve_name = libseccomp.seccomp_syscall_resolve_name
        seccomp_syscall_resolve_name.argtypes = (c_char_p, )
        seccomp_syscall_resolve_name.restype = c_int
        self.syscall_resolve_name: Callable[[c_char_p], c_int] = (
            seccomp_syscall_resolve_name
        )

        seccomp_rule_add = libseccomp.seccomp_rule_add
        seccomp_rule_add.argtypes = (c_void_p, c_uint32, c_int, c_uint)
        seccomp_rule_add.restype = c_int
        self.rule_add: Callable[[c_void_p, c_uint32, c_int, c_uint], c_int] = (
            seccomp_rule_add
        )

        seccomp_export_pfc = libseccomp.seccomp_export_pfc
        seccomp_export_pfc.argtypes = (c_void_p, c_int)
        seccomp_export_pfc.restype = c_int
        self.export_pfc: Callable[[c_void_p, c_int], c_int] = (
            seccomp_export_pfc
        )

        seccomp_export_bpf = libseccomp.seccomp_export_bpf
        seccomp_export_bpf.argtypes = (c_void_p, c_int)
        seccomp_export_bpf.restype = c_int
        self.export_bpf: Callable[[c_void_p, c_int], c_int] = (
            seccomp_export_bpf
        )

        seccomp_arch_add = libseccomp.seccomp_arch_add
        seccomp_arch_add.argtypes = (c_void_p, c_uint32)
        seccomp_arch_add.restype = c_int
        self.arch_add: Callable[[c_void_p, c_uint32], c_int] = (
            seccomp_arch_add
        )


class SeccompState:

    def __init__(self) -> None:
        self.libseccomp = Libseccomp()

        self._seccomp_ruleset_ptr = self.libseccomp.init(SCMP_ACT_ALLOW)

        if machine() == 'x86_64':
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
        if isinstance(directive, SeccompSyscallErrno):
            self.filter_syscall(directive.syscall_name, directive.errno)
        else:
            raise TypeError('Unknown seccomp directive.')

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

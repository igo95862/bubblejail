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


from ctypes import CDLL, c_char_p, c_int, c_uint, c_uint32, c_void_p
from ctypes.util import find_library
from tempfile import TemporaryFile
from typing import IO, Callable, Tuple, Type, TypeVar, cast

from .bwrap_config import SeccompDirective, SeccompSyscallErrno

libseccomp = CDLL(find_library('seccomp'))

T = TypeVar('T')
T2 = TypeVar('T2')


def import_from_cdll(
    func_name: str,
        arg_list: Tuple[Type[T2], ...],
        return_type: Type[T]) -> Callable[..., T]:
    c_function = getattr(libseccomp, func_name)
    c_function.argtypes = arg_list
    c_function.restype = return_type
    return cast(Callable[[T2], T], c_function)


seccomp_init = import_from_cdll('seccomp_init', (c_uint, ), c_void_p)
seccomp_load = import_from_cdll('seccomp_load', (c_void_p, ), c_int)
seccomp_syscall_resolve_name = import_from_cdll(
    'seccomp_syscall_resolve_name', (c_char_p, ), c_int)
seccomp_rule_add = import_from_cdll(
    'seccomp_rule_add', (c_void_p, c_uint32, c_int, c_uint), c_int)
seccomp_export_pfc = import_from_cdll(
    'seccomp_export_pfc', (c_void_p, c_int), c_int)
seccomp_export_bpf = import_from_cdll(
    'seccomp_export_bpf', (c_void_p, c_int), c_int)
seccomp_arch_add = import_from_cdll(
    'seccomp_arch_add', (c_void_p, c_uint32), c_int)

SCMP_ACT_ALLOW = c_uint(0x7fff0000)

ARCH_X86 = c_uint32(3 | 0x40000000)


def get_scmp_act_errno(error_code: int) -> c_uint32:
    return c_uint32(0x00050000 | (error_code & 0x0000ffff))


class SeccompState:

    def __init__(self) -> None:
        self._seccomp_ruleset_ptr: c_void_p = seccomp_init(SCMP_ACT_ALLOW)
        # HACK: Assuming 99.9 percent of people will use x86_64 we only
        # need to add x86 for compatibilities with 32 bit applications
        # I you plan on using bubblejail on ARM or any other arch
        # please open issue on github
        seccomp_arch_add(self._seccomp_ruleset_ptr, ARCH_X86)

    def filter_syscall(self, syscall_name: str, error_number: int) -> None:
        resolved_syscall_int = seccomp_syscall_resolve_name(
            c_char_p(syscall_name.encode())
        )

        seccomp_rule_add(
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
        seccomp_load(self._seccomp_ruleset_ptr)

    def export_to_temp_file(self) -> IO[bytes]:
        t = TemporaryFile()
        seccomp_export_bpf(self._seccomp_ruleset_ptr, t.fileno())
        t.seek(0)
        return t

    def print(self) -> None:
        seccomp_export_pfc(self._seccomp_ruleset_ptr, 0)

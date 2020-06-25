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


from ctypes import CDLL, c_int, c_uint, c_void_p
from ctypes.util import find_library
from typing import Any, List

libseccomp = CDLL(find_library('seccomp'))


def import_from_cdll(
        func_name: str, arg_list: List[Any], return_type: Any) -> Any:
    c_function = getattr(libseccomp, func_name)
    c_function.argtypes = arg_list
    c_function.restype = return_type
    return c_function


seccomp_init = import_from_cdll('seccomp_init', [c_uint], c_void_p)
seccomp_load = import_from_cdll('seccomp_load', [c_void_p], c_int)

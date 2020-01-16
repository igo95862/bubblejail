# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019 igo95862

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


from xdg import BaseDirectory
from os import environ
from .bwrap_config import (BwrapArgs, Bind, ReadOnlyBind,
                           EnvrimentalVar)

X11 = BwrapArgs(
    binds=[Bind(f"/tmp/.X11-unix/X{environ['DISPLAY'][1:]}")],
    env_no_unset={'DISPLAY',
                  'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION',
                  'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP'},
    read_only_binds=[ReadOnlyBind('/etc/fonts/fonts.conf')],
)

Wayland = BwrapArgs(
    binds=[Bind((f"{BaseDirectory.get_runtime_dir()}"
                 f"/{environ['WAYLAND_DISPLAY']}")), ],
    env_no_unset={'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR',
                  'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION',
                  'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP'},
    enviromental_variables=[EnvrimentalVar('GDK_BACKEND', 'wayland')])

Network = BwrapArgs()
Network.share_network = True

PulseAudio = BwrapArgs(
    binds=[
        Bind(f"{BaseDirectory.get_runtime_dir()}/pulse/native"),
    ],
    env_no_unset={'XDG_RUNTIME_DIR'},

)

__all__ = ["X11", "Network"]

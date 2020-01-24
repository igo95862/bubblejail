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


from os import environ
from typing import Callable, Dict, FrozenSet, List

from xdg import BaseDirectory

from .bwrap_config import Bind, BwrapConfig, EnvrimentalVar, ReadOnlyBind

XDG_DESKTOP_VARS: FrozenSet[str] = frozenset({
    'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION',
    'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP'})


def x11() -> BwrapConfig:
    return BwrapConfig(
        env_no_unset=XDG_DESKTOP_VARS.union(('DISPLAY',)),
        binds=(
            Bind(f"/tmp/.X11-unix/X{environ['DISPLAY'][1:]}"),
        ),
        read_only_binds=(
            ReadOnlyBind(environ['XAUTHORITY'], '/tmp/.Xauthority'),
            ReadOnlyBind('/etc/fonts/fonts.conf'),
        ),
        enviromental_variables=(
            EnvrimentalVar('XAUTHORITY', '/tmp/.Xauthority'),
        )
    )


def wayland() -> BwrapConfig:
    return BwrapConfig(
        env_no_unset=XDG_DESKTOP_VARS.union(('WAYLAND_DISPLAY',)),
        enviromental_variables=(
            EnvrimentalVar('GDK_BACKEND', 'wayland'),
        ),
        binds=(
            Bind((
                f"{BaseDirectory.get_runtime_dir()}"
                f"/{environ.get('WAYLAND_DISPLAY')}")),
        ),
    )


def network() -> BwrapConfig:
    return BwrapConfig(share_network=True)


def pulse_audio() -> BwrapConfig:
    return BwrapConfig(
        env_no_unset=frozenset(('XDG_RUNTIME_DIR', )),
        binds=(
            Bind(f"{BaseDirectory.get_runtime_dir()}/pulse/native"),
        ),
    )


def gnome_tool_kit(name: str) -> BwrapConfig:
    return BwrapConfig(
        extra_args=(
            '--class', f"bubble_{name}",
            '--name', f"bubble_{name}")
    )


def home_share(home_paths: List[str]) -> BwrapConfig:
    return BwrapConfig(
        binds=tuple((Bind(environ['HOME'] + x, '/home/user' + x)
                     for x in home_paths))
    )


SERVICES: Dict[str, Callable[..., BwrapConfig]] = {
    'x11': x11,
    'wayland': wayland,
    'network': network,
    'pulse_audio': pulse_audio,
    'gnome_tool_kit': gnome_tool_kit,
    'home_share': home_share,
}

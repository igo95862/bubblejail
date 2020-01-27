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
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Set

from xdg import BaseDirectory

from .bwrap_config import (Bind, BwrapConfig, DevBind, DirCreate,
                           EnvrimentalVar, FileTransfer, ReadOnlyBind, Symlink)

XDG_DESKTOP_VARS: FrozenSet[str] = frozenset({
    'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION',
    'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP'})


def generate_path_var() -> str:
    """Filters PATH variable to locations with /usr prefix"""

    # Split by semicolon
    paths = environ['PATH'].split(':')
    # Insert /tmp/bin infront for hacks like steam with pulseaudio
    # O(n) insertion but PATH should never be large
    paths.insert(0, '/tmp/bin')
    # Filter by /usr and /tmp then join by semicolon
    return ':'.join(filter(
        lambda s: s.startswith('/usr/') or s.startswith('/tmp/'),
        paths))


DEFAULT_CONFIG = BwrapConfig(
    read_only_binds=(
        ReadOnlyBind('/usr'),
        ReadOnlyBind('/etc/resolv.conf'),
        ReadOnlyBind('/etc/login.defs'),  # ???: is this file needed
        ReadOnlyBind('/etc/fonts/'),
        ReadOnlyBind('/opt'),
    ),

    dir_create=(
        DirCreate('/tmp'),
        DirCreate('/var'),
        DirCreate('/home/user'),
        DirCreate('/run/user/1000'),
    ),

    symlinks=(
        Symlink('usr/lib', '/lib'),
        Symlink('usr/lib64', '/lib64'),
        Symlink('usr/bin', '/bin'),
        Symlink('usr/sbin', '/sbin')
    ),

    files=(
        FileTransfer(
            b'user:x:1000:1000::/home/user:/bin/sh',
            '/etc/passwd'),

        FileTransfer(
            b'user:x:1000:',
            '/etc/group'),
    ),

    enviromental_variables=(
        EnvrimentalVar('USER', 'user'),
        EnvrimentalVar('USERNAME', 'user'),
        EnvrimentalVar('HOME', '/home/user'),
        EnvrimentalVar('PATH', generate_path_var()),
        EnvrimentalVar('XDG_RUNTIME_DIR', '/run/user/1000'),
    ),

    env_no_unset=frozenset(
        (
            'LANG'
        )
    )
)


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
    return BwrapConfig(
        share_network=True,
        read_only_binds=(
            ReadOnlyBind('/etc/ca-certificates'),
            ReadOnlyBind('/etc/ssl'),
        )
    )


def pulse_audio() -> BwrapConfig:
    return BwrapConfig(
        env_no_unset=frozenset(('XDG_RUNTIME_DIR', )),
        binds=(
            Bind(f"{BaseDirectory.get_runtime_dir()}/pulse/native"),
        ),
        symlinks=(  # Steam hack but seems to be caused by arch linux patch
            Symlink('/usr/bin/true', '/tmp/bin/pulseaudio'),
        )
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


def direct_rendering() -> BwrapConfig:
    # TODO: Allow to select which DRM devices to pass

    # Bind /dev/dri and /sys/dev/char and /sys/devices
    symlinks: List[Symlink] = []

    final_paths: Set[str] = set()
    # Get names of cardX and renderX in /dev/dri
    dev_dri_path = Path('/dev/dri/')
    device_names = set()
    for x in dev_dri_path.iterdir():
        if x.is_char_device():
            device_names.add(x.stem)

    # Resolve links in /sys/dev/char/
    sys_dev_char_path = Path('/sys/dev/char/')
    # For each symlink in /sys/dev/char/ resolve
    # and see if they point to cardX or renderX
    for x in sys_dev_char_path.iterdir():
        x_resolved = x.resolve()
        if x_resolved.stem in device_names:
            # Found the dri device
            # Add the /sys/dev/char/ path
            symlinks.append(Symlink(str(x_resolved), str(x)))
            # Add the two times parent (parents[1])
            # Seems like the dri devices are stored as
            # /sys/devices/..pcie_id../drm/dri
            # We want to bind the /sys/devices/..pcie_id../
            final_paths.add(str(x_resolved.parents[1]))

    dri_binds = [DevBind('/dev/dri')]
    dri_binds.extend((DevBind(x) for x in final_paths))

    return BwrapConfig(
        binds=tuple(dri_binds),
        symlinks=tuple(symlinks),
    )


SERVICES: Dict[str, Callable[..., BwrapConfig]] = {
    'x11': x11,
    'wayland': wayland,
    'network': network,
    'pulse_audio': pulse_audio,
    'gnome_tool_kit': gnome_tool_kit,
    'home_share': home_share,
    'direct_rendering': direct_rendering,
}

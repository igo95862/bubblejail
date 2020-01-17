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

from xdg import BaseDirectory

from .bubblejail_instance import BubblejailInstance
from .bwrap_config import Bind, BwrapArgs, EnvrimentalVar, ReadOnlyBind

# TODO: Better handle missing resources such as no Wayland under pure X11


XDG_DESKTOP_VARS = (
    'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION',
    'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP')


class BubblejailService(BwrapArgs):
    def __init__(self, instance: BubblejailInstance):
        super().__init__()
        self.instance = instance


class X11(BubblejailService):

    def __init__(self, instance: BubblejailInstance) -> None:
        super().__init__(instance)
        self.env_no_unset.update(XDG_DESKTOP_VARS)
        self.binds.append(Bind(f"/tmp/.X11-unix/X{environ['DISPLAY'][1:]}"))
        self.env_no_unset.add('DISPLAY')
        self.read_only_binds.append(
            ReadOnlyBind(environ['XAUTHORITY'], '/tmp/.Xauthority'))
        self.read_only_binds.append(ReadOnlyBind('/etc/fonts/fonts.conf'))
        self.enviromental_variables.append(
            EnvrimentalVar('XAUTHORITY', '/tmp/.Xauthority'))


class Wayland(BubblejailService):

    def __init__(self, instance: BubblejailInstance):
        super().__init__(instance)
        self.env_no_unset.update(XDG_DESKTOP_VARS)
        self.enviromental_variables.append(
            EnvrimentalVar('GDK_BACKEND', 'wayland')
        )
        self.binds.append(
            Bind((
                f"{BaseDirectory.get_runtime_dir()}"
                f"/{environ.get('WAYLAND_DISPLAY')}"))
        )
        self.env_no_unset.add('WAYLAND_DISPLAY')


class Network(BubblejailService):

    def __init__(self, instance: BubblejailInstance):
        super().__init__(instance)
        self.share_network = True


class PulseAudio(BubblejailService):

    def __init__(self, instance: BubblejailInstance) -> None:
        super().__init__(instance)
        self.env_no_unset.add('XDG_RUNTIME_DIR')
        self.binds.append(
            Bind(f"{BaseDirectory.get_runtime_dir()}/pulse/native"))


class GnomeToolKit(BubblejailService):
    def __init__(self, instance: BubblejailInstance):
        super().__init__(instance)
        self.extra_args.extend(
            ('--class', f"bubble_{instance.name}",
             '--name', f"bubble_{instance.name}"))


__all__ = ["X11", "Wayland", "PulseAudio", "Network", "GnomeToolKit"]

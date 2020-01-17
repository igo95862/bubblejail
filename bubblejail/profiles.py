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


from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Type

from .bubblejail_instance import BubblejailInstance
from .bwrap_config import DEFAULT_CONFIG, Bind, BwrapArgs
from .services import (X11, BubblejailService, GnomeToolKit, Network,
                       PulseAudio, Wayland)


@dataclass
class BubblejailBaseProfile:
    executable_name: str
    import_paths: List[str] = field(default_factory=list)
    services: List[Type[BubblejailService]] = field(default_factory=list)

    def generate_bw_args(self, home_path: Path,
                         instance: BubblejailInstance) -> BwrapArgs:
        new_args = BwrapArgs()
        for x in self.services:
            service = x(instance)
            new_args.extend(service)
        new_args.extend(DEFAULT_CONFIG)
        new_args.binds.append(Bind(str(home_path), '/home/user'))
        return new_args


FIREFOX_PROFILE = BubblejailBaseProfile(
    import_paths=[f'{Path.home()}/.mozzila/firefox'],
    services=[X11, Network, PulseAudio, GnomeToolKit],
    executable_name='firefox',
)

FIREFOX_WAYLAND_PROFILE = BubblejailBaseProfile(
    import_paths=[f'{Path.home()}/.mozzila/firefox'],
    services=[Wayland, Network, PulseAudio, GnomeToolKit],
    executable_name='firefox',
)

applications: Dict[str, BubblejailBaseProfile] = {
    'firefox': FIREFOX_PROFILE,
    'firefox_wayland': FIREFOX_WAYLAND_PROFILE,
}

__all__ = ["FIREFOX_PROFILE"]

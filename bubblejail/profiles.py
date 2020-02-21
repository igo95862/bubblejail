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


from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .bubblejail_instance_config import BubblejailInstanceConfig


@dataclass
class BubblejailProfile:
    default_instance_config: BubblejailInstanceConfig
    dot_desktop_path: Path
    import_paths: List[str] = field(default_factory=list)


FIREFOX_PROFILE = BubblejailProfile(
    import_paths=[f'{Path.home()}/.mozzila/firefox'],
    default_instance_config=BubblejailInstanceConfig(
        executable_name='firefox',
        services={
            'x11': {},
            'network': {},
            'pulse_audio': {},
            'gnome_tool_kit': {'name': 'required'},
            'home_share': {'home_paths': ['/Downloads']},
        }
    ),
    dot_desktop_path=Path('/usr/share/applications/firefox.desktop')
)

FIREFOX_WAYLAND_PROFILE = BubblejailProfile(
    import_paths=[f'{Path.home()}/.mozzila/firefox'],
    default_instance_config=BubblejailInstanceConfig(
        executable_name='firefox',
        services={
            'wayland': {},
            'network': {},
            'pulse_audio': {},
            'gnome_tool_kit': {'name': 'required'},
            'home_share': {'home_paths': ['/Downloads']},
        }
    ),
    dot_desktop_path=Path('/usr/share/applications/firefox.desktop')
)

CODE_OSS = BubblejailProfile(
    import_paths=[''],
    default_instance_config=BubblejailInstanceConfig(
        executable_name=['code-oss', '--wait'],
        services={
            'x11': {},
            'network': {},
            'home_share': {'home_paths': ['/Projects']},
        }
    ),
    dot_desktop_path=Path('/usr/share/applications/code-oss.desktop')
)

STEAM = BubblejailProfile(
    import_paths=[''],
    default_instance_config=BubblejailInstanceConfig(
        executable_name='steam',
        services={
            'x11': {},
            'pulse_audio': {},
            'network': {},
            'direct_rendering': {},
            'joystick': {},
        }
    ),
    dot_desktop_path=Path('/usr/share/applications/steam.desktop'),
)

LUTRIS = BubblejailProfile(
    import_paths=[''],
    default_instance_config=BubblejailInstanceConfig(
        executable_name='lutris',
        services={
            'x11': {},
            'pulse_audio': {},
            'network': {},
            'direct_rendering': {},
            'joystick': {},
            'openjdk': {},
        }
    ),
    dot_desktop_path=Path('/usr/share/applications/net.lutris.Lutris.desktop'),
)


PROFILES: Dict[str, BubblejailProfile] = {
    'firefox': FIREFOX_PROFILE,
    'firefox_wayland': FIREFOX_WAYLAND_PROFILE,
    'code_oss': CODE_OSS,
    'steam': STEAM,
    'lutris': LUTRIS,
}

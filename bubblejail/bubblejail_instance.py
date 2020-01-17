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

from json import dump as json_dump
from json import load as json_load
from os import environ
from pathlib import Path
from typing import List, Optional

from xdg import IniFile
from xdg.BaseDirectory import xdg_data_home
from xdg.Exceptions import NoKeyError as XdgNoKeyError

from .exceptions import BubblejailException


def get_data_directory() -> Path:
    # Check if XDG_DATA_HOME is set
    try:
        data_path = Path(environ['XDG_DATA_HOME'] + "/bubblejail")
    except KeyError:
        # Default to ~/.local/share/bubblejail
        data_path = Path(Path.home(), ".local/share/bubblejail")

    # Create directory if neccesary
    if not data_path.is_dir():
        data_path.mkdir(mode=0o700)

    return data_path


class BubblejailInstance:
    def __init__(self, name: str, args_to_run: Optional[List[str]] = None):
        self.name = name
        self.args_to_run = args_to_run
        self.instance_directory = get_data_directory() / self.name
        if not (
            (self.instance_directory.exists())
                and (self.instance_directory.is_dir())):
            raise BubblejailException("Instance directory does not exists")

    def _read_config(self) -> str:

        with (self.instance_directory / "config.json").open() as f:
            instance_config = json_load(f)

        profile_name: str = instance_config['profile']
        return profile_name

    def generate_dot_desktop(self, dot_desktop_path: str) -> None:
        new_dot_desktop = IniFile.IniFile(
            filename=dot_desktop_path)

        # Strip non Desktop Entry groups
        # TODO: Modify actions instead of removing
        groups_to_remove = []
        for g in new_dot_desktop.groups():
            if g != "Desktop Entry":
                groups_to_remove.append(g)

        for g in groups_to_remove:
            new_dot_desktop.removeGroup(g)

        # Remove Actions= from Desktop Entry
        try:
            new_dot_desktop.removeKey(
                key='Actions',
                group='Desktop Entry'
            )
        except XdgNoKeyError:
            ...
        # Modify Exec
        old_exec = new_dot_desktop.get(
            key='Exec', group='Desktop Entry'
        )

        new_dot_desktop.set(
            key='Exec',
            value=(f"bubblejail run {self.name} "
                   f"{' '.join(old_exec.split()[1:])}"),
            group='Desktop Entry')

        # Modify name
        new_dot_desktop.set(
            key="Name",
            group='Desktop Entry',
            value=f"{self.name} bubble",
        )

        # Modify StartupWMClass
        new_dot_desktop.set(
            key="StartupWMClass",
            group='Desktop Entry',
            value=f"bubble_{self.name}",
        )

        dot_desktop_path = (
            f"{xdg_data_home}/applications/bubble_{self.name}.desktop")

        new_dot_desktop.write(filename=dot_desktop_path)

    @staticmethod
    def create_new(new_name: str, profile_name: str) -> 'BubblejailInstance':
        instance_directory = get_data_directory() / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700)
        # Make home directory
        (instance_directory / 'home').mkdir(mode=0o700)
        # Make config.json
        with (instance_directory / 'config.json').open(mode='x') as f:
            json_dump({'profile': profile_name}, f)

        instance = BubblejailInstance(new_name)
        return instance

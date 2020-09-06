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

from os import environ
from pathlib import Path
from typing import Generator, Optional

from toml import dump as toml_dump
from xdg import IniFile
from xdg.BaseDirectory import xdg_data_home

from .bubblejail_instance import BubblejailInstance, BubblejailProfile
from .exceptions import BubblejailException

PathGeneratorType = Generator[Path, None, None]


class BubblejailDirectories:

    @classmethod
    def instance_get(cls, instance_name: str) -> BubblejailInstance:
        for instances_dir in cls.iter_instances_directories():
            possible_instance_path = instances_dir / instance_name

            if possible_instance_path.is_dir():
                return BubblejailInstance(possible_instance_path)

        raise BubblejailException(f"Instance not found {instance_name}")

    @classmethod
    def create_new_instance(
            cls,
            new_name: str,
            profile: Optional[BubblejailProfile] = None,
            create_dot_desktop: bool = False,
    ) -> BubblejailInstance:

        instance_directory = next(cls.iter_instances_directories()) / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700, parents=True)
        # Make home directory
        (instance_directory / 'home').mkdir(mode=0o700)
        # Make config.json
        with (instance_directory / 'services.toml').open(
                mode='x') as instance_conf_file:

            if profile is not None:
                service_conf_dict = profile.config.get_service_conf_dict()
            else:
                service_conf_dict = {}

            toml_dump(service_conf_dict, instance_conf_file)

        instance = BubblejailInstance(instance_directory)

        if create_dot_desktop:
            cls.generate_dot_desktop(
                instance_name=new_name,
                dot_desktop_path=(
                    profile.dot_desktop_path if profile is not None else None)
            )

        return instance

    @classmethod
    def iter_bubblejail_data_directories(cls) -> PathGeneratorType:
        # TODO: Add ability to create custom data directories
        try:
            data_directories = environ['BUBBLEJAIL_DATADIRS']
        except KeyError:
            yield Path(xdg_data_home + '/bubblejail')
            return

        yield from (Path(x) for x in data_directories.split(':'))

    @classmethod
    def iter_instances_directories(cls) -> PathGeneratorType:
        for data_dir in cls.iter_bubblejail_data_directories():
            yield (data_dir / 'instances')

    @classmethod
    def iter_instances_path(cls) -> PathGeneratorType:
        for instances_dir in cls.iter_instances_directories():
            yield from instances_dir.iterdir()

    @classmethod
    def desktop_entries_dir_get(cls) -> Path:
        return Path(xdg_data_home + '/applications')

    @classmethod
    def generate_dot_desktop(
            cls,
            instance_name: str,
            create_new_entry: bool = True,
            dot_desktop_path: Optional[Path] = None,
    ) -> None:

        if dot_desktop_path is not None:
            new_dot_desktop = IniFile.IniFile(
                filename=str(dot_desktop_path))

            for group_name in new_dot_desktop.groups():
                # Modify Exec
                old_exec = new_dot_desktop.get(
                    key='Exec', group=group_name
                )
                if not old_exec:
                    continue

                new_dot_desktop.set(
                    key='Exec',
                    value=(f"bubblejail run {instance_name} "
                           f"{' '.join(old_exec.split()[1:])}"),
                    group=group_name)

        else:
            new_dot_desktop = IniFile.IniFile()
            new_dot_desktop.addGroup('Desktop Entry')
            new_dot_desktop.set(
                key='Exec',
                value=f"bubblejail run {instance_name}",
                group='Desktop Entry'
            )

        # Modify name
        new_dot_desktop.set(
            key="Name",
            group='Desktop Entry',
            value=f"{instance_name} bubble",
        )

        # Modify StartupWMClass
        new_dot_desktop.set(
            key="StartupWMClass",
            group='Desktop Entry',
            value=f"bubble_{instance_name}",
        )

        if create_new_entry:
            new_dot_desktop_path_str = str(
                cls.desktop_entries_dir_get() /
                f"bubble_{instance_name}.desktop")
        else:
            if dot_desktop_path is None:
                raise RuntimeError(
                    'Attempted to overwrite unknown desktop entry')

            new_dot_desktop_path_str = str(dot_desktop_path)

        new_dot_desktop.write(filename=new_dot_desktop_path_str)

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
from typing import Any, Dict, Generator, Optional

from toml import dump as toml_dump
from toml import load as toml_load
from xdg import IniFile
from xdg.BaseDirectory import xdg_data_home

from .bubblejail_instance import BubblejailInstance, BubblejailProfile
from .bubblejail_utils import FILE_NAME_SERVICES
from .exceptions import BubblejailException, BubblejailInstanceNotFoundError

PathGeneratorType = Generator[Path, None, None]

UsrSharePath = Path('/usr/share/')
UsrShareApplicationsPath = UsrSharePath / 'applications'
SystemConfigsPath = UsrSharePath / 'bubblejail'


def convert_old_conf_to_new() -> None:
    for instance_directory in BubblejailDirectories.\
            iter_instances_path():
        if (instance_directory / FILE_NAME_SERVICES).is_file():
            continue

        print(f"Converting {instance_directory.stem}")

        old_conf_path = instance_directory / 'config.toml'
        with open(old_conf_path) as old_conf_file:
            old_conf_dict = toml_load(old_conf_file)

        new_conf: Dict[str, Any] = {}

        try:
            services_list = old_conf_dict.pop('services')
        except KeyError:
            services_list = []

        for service_name in services_list:
            new_conf[service_name] = {}

        try:
            old_service_dict = old_conf_dict.pop('service')
        except KeyError:
            old_service_dict = {}

        for service_name, service_dict in old_service_dict.items():
            new_conf[service_name] = service_dict

        new_conf['common'] = old_conf_dict

        with open(instance_directory / FILE_NAME_SERVICES, mode='x') as f:
            toml_dump(new_conf, f)


class BubblejailDirectories:

    @classmethod
    def instance_get(cls, instance_name: str) -> BubblejailInstance:
        convert_old_conf_to_new()
        for instances_dir in cls.iter_instances_directories():
            possible_instance_path = instances_dir / instance_name

            if possible_instance_path.is_dir():
                return BubblejailInstance(possible_instance_path)

        raise BubblejailInstanceNotFoundError(instance_name)

    @classmethod
    def profile_get(cls, profile_name: str) -> BubblejailProfile:
        profile_file_name = profile_name + '.toml'
        for profiles_directory in cls.iter_profile_directories():
            possible_profile_path = profiles_directory / profile_file_name

            if possible_profile_path.is_file():
                with open(possible_profile_path) as profile_file:
                    return BubblejailProfile(**toml_load(profile_file))

        raise BubblejailException(f"Profile {profile_name} not found")

    @classmethod
    def iter_profile_directories(cls) -> PathGeneratorType:
        for conf_dir in cls.iterm_config_dirs():
            yield conf_dir / 'profiles'

    @classmethod
    def iterm_config_dirs(cls) -> PathGeneratorType:
        try:
            conf_directories = environ['BUBBLEJAIL_CONFDIRS']
        except KeyError:
            # TODO: add user directory
            yield SystemConfigsPath
            return

        yield from (Path(x) for x in conf_directories.split(':'))

    @classmethod
    def create_new_instance(
            cls,
            new_name: str,
            profile_name: Optional[str] = None,
            create_dot_desktop: bool = False,
    ) -> BubblejailInstance:

        instance_directory = next(cls.iter_instances_directories()) / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700, parents=True)
        # Make home directory
        (instance_directory / 'home').mkdir(mode=0o700)

        # Profile
        profile: BubblejailProfile = cls.profile_get(
            profile_name) if profile_name is not None else BubblejailProfile()

        # Make config.json
        with (instance_directory / FILE_NAME_SERVICES).open(
                mode='x') as instance_conf_file:

            toml_dump(profile.config.get_service_conf_dict(),
                      instance_conf_file)

        instance = BubblejailInstance(instance_directory)

        if create_dot_desktop:
            if profile.dot_desktop_path is not None:
                cls.overwrite_desktop_entry_for_profile(
                    instance_name=new_name,
                    profile_object=profile,
                )
            else:
                cls.generate_empty_desktop_entry(new_name)

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
    def desktop_entry_name_to_path(cls,
                                   desktop_entry_name: str) -> Optional[Path]:
        if '/' not in desktop_entry_name:
            # Desktop entry was passed without absolute or relative path
            if not desktop_entry_name.endswith('.desktop'):
                possible_name = desktop_entry_name + '.desktop'
            else:
                possible_name = desktop_entry_name
            possible_path = UsrShareApplicationsPath / possible_name
        else:
            possible_path = Path(desktop_entry_name)

        if possible_path.is_file():
            return possible_path

        return None

    @classmethod
    def overwrite_desktop_entry_for_profile(
        cls, instance_name: str,
        profile_object: Optional[BubblejailProfile] = None,
        profile_name: Optional[str] = None,
        desktop_entry_name: Optional[str] = None,
        new_name: Optional[str] = None,
    ) -> None:

        if profile_object is not None:
            profile = profile_object
            dot_desktop_path = profile.dot_desktop_path
        elif profile_name is not None:
            profile = cls.profile_get(profile_name)
            dot_desktop_path = profile.dot_desktop_path
        elif desktop_entry_name is not None:
            dot_desktop_path = cls.desktop_entry_name_to_path(
                desktop_entry_name)
        else:
            raise RuntimeError('No profile or desktop entry specified')

        if dot_desktop_path is None:
            raise TypeError('Desktop entry path can\'t be None.',
                            dot_desktop_path)

        cls.instance_get(instance_name)

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
                       f"{' '.join(old_exec.split())}"),
                group=group_name)

        # Modify name
        new_dot_desktop.set(
            key="Name",
            group='Desktop Entry',
            value=f"{instance_name} bubble",
        )

        new_dot_desktop.write(
            filename=(cls.desktop_entries_dir_get() / dot_desktop_path.name)
        )

    @classmethod
    def generate_empty_desktop_entry(
            cls,
            instance_name: str,
    ) -> None:

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

        new_dot_desktop_path_str = str(
            cls.desktop_entries_dir_get() /
            f"bubble_{instance_name}.desktop")

        new_dot_desktop.write(filename=new_dot_desktop_path_str)

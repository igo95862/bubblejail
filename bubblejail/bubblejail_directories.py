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
from typing import Any, Dict, Generator, Optional, Union

from toml import dump as toml_dump
from toml import load as toml_load
from xdg import IniFile
from xdg.BaseDirectory import xdg_data_home

from .bubblejail_instance import BubblejailInstance, BubblejailProfile
from .bubblejail_utils import FILE_NAME_SERVICES
from .exceptions import BubblejailException

PathGeneratorType = Generator[Path, None, None]

SystemConfigsPath = Path('/usr/share/bubblejail')


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

        raise BubblejailException(f"Instance not found {instance_name}")

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
            profile: Optional[Union[BubblejailProfile, str]] = None,
            create_dot_desktop: bool = False,
    ) -> BubblejailInstance:

        instance_directory = next(cls.iter_instances_directories()) / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700, parents=True)
        # Make home directory
        (instance_directory / 'home').mkdir(mode=0o700)
        # Make config.json
        with (instance_directory / FILE_NAME_SERVICES).open(
                mode='x') as instance_conf_file:

            if isinstance(profile, str):
                profile = cls.profile_get(profile)
            elif profile is None:
                profile = BubblejailProfile()

            toml_dump(profile.config.get_service_conf_dict(),
                      instance_conf_file)

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
    def overwrite_desktop_entry_for_profile(
        cls, instance_name: str,
        profile_name: str,
        new_name: Optional[str] = None,
    ) -> None:
        profile = cls.profile_get(profile_name)

        dot_desktop_path = profile.dot_desktop_path

        if dot_desktop_path is None:
            raise TypeError('Desktop entry path can\'t be None')

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

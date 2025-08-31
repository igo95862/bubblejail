# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2022 igo95862
from __future__ import annotations

from os import environ
from pathlib import Path
from subprocess import run as subprocess_run
from sys import stderr
from tomllib import load as toml_load
from typing import TYPE_CHECKING

from tomli_w import dump as toml_dump
from xdg import IniFile
from xdg.BaseDirectory import xdg_config_home, xdg_data_home

from .bubblejail_instance import BubblejailInstance, BubblejailProfile
from .bubblejail_utils import FILE_NAME_SERVICES, BubblejailSettings
from .exceptions import BubblejailException, BubblejailInstanceNotFoundError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    PathGeneratorType = Iterator[Path]

UsrSharePath = Path(BubblejailSettings.SHARE_PATH_STR)
SysConfPath = Path(BubblejailSettings.SYSCONF_PATH_STR)

UsrShareApplicationsPath = UsrSharePath / "applications"

PackageConfisgPath = UsrSharePath / "bubblejail"
SystemConfigsPath = SysConfPath / "bubblejail"
UserConfigDir = Path(xdg_config_home) / "bubblejail"


def convert_old_conf_to_new() -> None:
    for instance_directory in BubblejailDirectories.iter_instances_path():
        if (instance_directory / FILE_NAME_SERVICES).is_file():
            continue

        print(f"Converting {instance_directory.stem}", file=stderr)

        old_conf_path = instance_directory / "config.toml"
        with open(old_conf_path, mode="rb") as old_conf_file:
            old_conf_dict = toml_load(old_conf_file)

        new_conf: dict[str, Any] = {}

        try:
            services_list = old_conf_dict.pop("services")
        except KeyError:
            services_list = []

        for service_name in services_list:
            new_conf[service_name] = {}

        try:
            old_service_dict = old_conf_dict.pop("service")
        except KeyError:
            old_service_dict = {}

        for service_name, service_dict in old_service_dict.items():
            new_conf[service_name] = service_dict

        new_conf["common"] = old_conf_dict

        with open(instance_directory / FILE_NAME_SERVICES, mode="xb") as f:
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
        profile_file_name = profile_name + ".toml"
        for profiles_directory in cls.iter_profile_directories():
            possible_profile_path = profiles_directory / profile_file_name

            try:
                with open(possible_profile_path, mode="rb") as profile_file:
                    return BubblejailProfile(**toml_load(profile_file))
            except FileNotFoundError:
                continue

        raise BubblejailException(f"Profile {profile_name} not found")

    @classmethod
    def iter_profile_names(cls) -> Iterator[str]:
        for profiles_directory in BubblejailDirectories.iter_profile_directories():
            try:
                for profile_file in profiles_directory.iterdir():
                    yield profile_file.stem
            except FileNotFoundError:
                continue

    @classmethod
    def iter_profile_directories(cls) -> PathGeneratorType:
        for conf_dir in cls.iterm_config_dirs():
            profiles_dir = conf_dir / "profiles"
            yield profiles_dir

    @classmethod
    def iterm_config_dirs(cls) -> PathGeneratorType:
        try:
            conf_directories = environ["BUBBLEJAIL_CONFDIRS"]
        except KeyError:
            UserConfigDir.mkdir(parents=True, exist_ok=True)
            yield UserConfigDir
            yield SystemConfigsPath
            yield PackageConfisgPath
            return

        yield from (Path(x) for x in conf_directories.split(":"))

    @classmethod
    def create_new_instance(
        cls,
        new_name: str,
        profile_name: str | None = None,
        create_dot_desktop: bool = False,
        print_import_tips: bool = False,
    ) -> BubblejailInstance:

        instance_directory = next(cls.iter_instances_directories()) / new_name

        # Exception will be raised if directory already exists
        instance_directory.mkdir(mode=0o700, parents=True)
        # Make home directory
        (instance_directory / "home").mkdir(mode=0o700)

        # Profile
        profile: BubblejailProfile = (
            cls.profile_get(profile_name)
            if profile_name is not None
            else BubblejailProfile()
        )

        # Make config.json
        with (instance_directory / FILE_NAME_SERVICES).open(
            mode="xb"
        ) as instance_conf_file:

            toml_dump(profile.config.get_service_conf_dict(), instance_conf_file)

        instance = BubblejailInstance(instance_directory)

        if create_dot_desktop:
            if profile.desktop_entries_paths:
                cls.overwrite_desktop_entry_for_profile(
                    instance_name=new_name,
                    profile_object=profile,
                )
            else:
                cls.generate_empty_desktop_entry(new_name)

        if profile_name is not None:
            instance.metadata_creation_profile_name = profile_name

        if profile_name is not None and print_import_tips:
            print("Import tips: ", profile.import_tips, file=stderr)

        return instance

    @classmethod
    def iter_bubblejail_data_directories(cls) -> PathGeneratorType:
        # TODO: Add ability to create custom data directories
        try:
            data_directories = environ["BUBBLEJAIL_DATADIRS"]
        except KeyError:
            home_path = Path(xdg_data_home + "/bubblejail")
            home_path.mkdir(exist_ok=True, parents=True)
            yield home_path
            return

        yield from (Path(x) for x in data_directories.split(":"))

    @classmethod
    def iter_instances_directories(cls) -> PathGeneratorType:
        for data_dir in cls.iter_bubblejail_data_directories():
            instances_dir_path = data_dir / "instances"
            instances_dir_path.mkdir(exist_ok=True)
            yield instances_dir_path

    @classmethod
    def iter_instances_path(cls) -> PathGeneratorType:
        for instances_dir in cls.iter_instances_directories():
            yield from instances_dir.iterdir()

    @classmethod
    def desktop_entries_dir_get(cls) -> Path:
        return Path(xdg_data_home + "/applications")

    @classmethod
    def desktop_entry_name_to_path(cls, desktop_entry_name: str) -> Path | None:
        if "/" not in desktop_entry_name:
            # Desktop entry was passed without absolute or relative path
            if not desktop_entry_name.endswith(".desktop"):
                possible_name = desktop_entry_name + ".desktop"
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
        cls,
        instance_name: str,
        profile_object: BubblejailProfile | None = None,
        profile_name: str | None = None,
        desktop_entry_name: str | None = None,
        new_name: str | None = None,
    ) -> None:

        instance = cls.instance_get(instance_name)

        # Five ways to figure out desktop entry path
        if desktop_entry_name is not None:
            # 1. Desktop entry path was passed.
            # 2. Desktop entry name was passed
            dot_desktop_path = cls.desktop_entry_name_to_path(desktop_entry_name)
        elif profile_object is not None:
            # 3. Profile was passed directly
            profile = profile_object
            dot_desktop_path = profile.find_desktop_entry()
        elif profile_name is not None:
            # 4. Profile name was passed
            profile = cls.profile_get(profile_name)
            dot_desktop_path = profile.find_desktop_entry()
        elif instance.metadata_creation_profile_name is not None:
            # 5. Use the profile name saved in meta data
            profile = cls.profile_get(instance.metadata_creation_profile_name)
            dot_desktop_path = profile.find_desktop_entry()
        else:
            raise RuntimeError("No profile or desktop entry specified")

        if dot_desktop_path is None:
            raise RuntimeError("Couldn't resolve desktop entry path.")

        new_dot_desktop = IniFile.IniFile(filename=str(dot_desktop_path))

        for group_name in new_dot_desktop.groups():
            # Modify Exec
            old_exec = new_dot_desktop.get(key="Exec", group=group_name)
            if not old_exec:
                continue

            new_dot_desktop.set(
                key="Exec",
                value=(
                    f"bubblejail run -- {instance_name} "
                    f"{' '.join(old_exec.split())}"
                ),
                group=group_name,
            )

        # Modify name
        new_dot_desktop.set(
            key="Name",
            group="Desktop Entry",
            value=f"{instance_name} bubble",
        )

        # Three ways to resolve what file to write to
        new_dot_desktop_path = cls.desktop_entries_dir_get() / dot_desktop_path.name
        if not new_dot_desktop_path.exists():
            # 1. If the entry under same name as the one
            #  we are overwriting does not exist use the same name
            #  and write meta data
            instance.metadata_desktop_entry_name = dot_desktop_path.name
        elif instance.metadata_desktop_entry_name == dot_desktop_path.name:
            # 2. If the instance already occupies the same name
            # keep the name
            ...
        else:
            # 3. Use the generic name
            new_dot_desktop_path = (
                cls.desktop_entries_dir_get() / f"bubble_{instance_name}.desktop"
            )

        new_dot_desktop.write(filename=str(new_dot_desktop_path))

        # Update desktop MIME database
        # Requires `update-desktop-database` binary
        # Arch package desktop-file-utils
        print("Updating desktop MIME database", file=stderr)
        cls.update_mime_database()

    @classmethod
    def update_mime_database(cls) -> None:
        try:
            subprocess_run(
                args=("update-desktop-database", str(cls.desktop_entries_dir_get()))
            )
        except FileNotFoundError:
            from warnings import warn

            warn(
                (
                    "Could not find update-desktop-database command. "
                    "Desktop entry database has not been updated."
                )
            )

    @classmethod
    def generate_empty_desktop_entry(
        cls,
        instance_name: str,
    ) -> None:

        new_dot_desktop = IniFile.IniFile()
        new_dot_desktop.addGroup("Desktop Entry")
        new_dot_desktop.set(
            key="Exec", value=f"bubblejail run {instance_name}", group="Desktop Entry"
        )

        # Modify name
        new_dot_desktop.set(
            key="Name",
            group="Desktop Entry",
            value=f"{instance_name} bubble",
        )

        # Add type
        new_dot_desktop.set(
            key="Type",
            group="Desktop Entry",
            value="Application",
        )

        new_dot_desktop_path_str = str(
            cls.desktop_entries_dir_get() / f"bubble_{instance_name}.desktop"
        )

        new_dot_desktop.write(filename=new_dot_desktop_path_str)

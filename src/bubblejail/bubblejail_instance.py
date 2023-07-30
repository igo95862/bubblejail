# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019-2022 igo95862

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
from __future__ import annotations

from asyncio import (
    CancelledError,
    create_subprocess_exec,
    open_unix_connection,
    wait_for,
)
from functools import cached_property
from os import environ, stat
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

try:
    from tomllib import loads as toml_loads
except ImportError:
    from tomli import loads as toml_loads
from tomli_w import dump as toml_dump
from xdg.BaseDirectory import get_runtime_dir

from .bubblejail_helper import RequestRun
from .bubblejail_runner import BubblejailRunner
from .bubblejail_utils import FILE_NAME_METADATA, FILE_NAME_SERVICES
from .exceptions import BubblejailException, BubblewrapRunError
from .services import ServiceContainer as BubblejailInstanceConfig
from .services import ServicesConfDictType


class BubblejailInstance:

    def __init__(self, instance_home: Path):
        self.name = instance_home.stem
        # Instance directory located at $XDG_DATA_HOME/bubblejail/
        self.instance_directory = instance_home
        # If instance directory does not exists we can't do much
        # Probably someone used 'run' command before 'create'
        if not self.instance_directory.exists():
            raise BubblejailException("Instance directory does not exist")

    # region Paths
    @cached_property
    def runtime_dir(self) -> Path:
        return Path(get_runtime_dir() + f'/bubblejail/{self.name}')

    @cached_property
    def path_config_file(self) -> Path:
        return self.instance_directory / FILE_NAME_SERVICES

    @cached_property
    def path_metadata_file(self) -> Path:
        return self.instance_directory / FILE_NAME_METADATA

    @cached_property
    def path_home_directory(self) -> Path:
        return self.instance_directory / 'home'

    @cached_property
    def path_runtime_helper_dir(self) -> Path:
        """Helper run-time directory"""
        return self.runtime_dir / 'helper'

    @cached_property
    def path_runtime_helper_socket(self) -> Path:
        return self.path_runtime_helper_dir / 'helper.socket'

    @cached_property
    def path_runtime_dbus_session_socket(self) -> Path:
        return self.runtime_dir / 'dbus_session_proxy'

    @cached_property
    def path_runtime_dbus_system_socket(self) -> Path:
        return self.runtime_dir / 'dbus_system_proxy'

    # endregion Paths

    # region Metadata

    def _get_metadata_dict(self) -> dict[str, Any]:
        try:
            with open(self.path_metadata_file) as metadata_file:
                return toml_loads(metadata_file.read())
        except FileNotFoundError:
            return {}

    def _save_metadata_key(self, key: str, value: Any) -> None:
        toml_dict = self._get_metadata_dict()
        toml_dict[key] = value

        with open(self.path_metadata_file, mode='wb') as metadata_file:
            toml_dump(toml_dict, metadata_file)

    def _get_metadata_value(self, key: str) -> str | None:
        try:
            value = self._get_metadata_dict()[key]
            if isinstance(value, str):
                return value
            else:
                raise TypeError(f"Expected str, got {value}")
        except KeyError:
            return None

    @property
    def metadata_creation_profile_name(self) -> str | None:
        return self._get_metadata_value('creation_profile_name')

    @metadata_creation_profile_name.setter
    def metadata_creation_profile_name(self, profile_name: str) -> None:
        self._save_metadata_key(
            key='creation_profile_name',
            value=profile_name,
        )

    @property
    def metadata_desktop_entry_name(self) -> str | None:
        return self._get_metadata_value('desktop_entry_name')

    @metadata_desktop_entry_name.setter
    def metadata_desktop_entry_name(self, desktop_entry_name: str) -> None:
        self._save_metadata_key(
            key='desktop_entry_name',
            value=desktop_entry_name,
        )

    # endregion Metadata

    def _read_config_file(self) -> str:
        with (self.path_config_file).open() as f:
            return f.read()

    def _read_config(
            self,
            config_contents: str | None = None) -> BubblejailInstanceConfig:

        if config_contents is None:
            config_contents = self._read_config_file()

        conf_dict = cast(ServicesConfDictType, toml_loads(config_contents))

        return BubblejailInstanceConfig(conf_dict)

    def save_config(self, config: BubblejailInstanceConfig) -> None:
        with open(self.path_config_file, mode='wb') as conf_file:
            toml_dump(config.get_service_conf_dict(), conf_file)

    async def send_run_rpc(
        self,
        args_to_run: list[str],
        wait_for_response: bool = False,
    ) -> str | None:
        (reader, writer) = await open_unix_connection(
            path=self.path_runtime_helper_socket,
        )

        request = RequestRun(
            args_to_run=args_to_run,
            wait_response=wait_for_response,
        )
        writer.write(request.to_json_byte_line())
        await writer.drain()

        try:
            if wait_for_response:
                data: str | None = request.decode_response(
                    await wait_for(
                        fut=reader.readline(),
                        timeout=3,
                    )
                )
            else:
                data = None
        finally:
            writer.close()
            await writer.wait_closed()

        return data

    def is_running(self) -> bool:
        return self.path_runtime_helper_socket.is_socket()

    async def async_run_init(
        self,
        args_to_run: list[str],
        debug_shell: bool = False,
        dry_run: bool = False,
        debug_helper_script: Path | None = None,
        debug_log_dbus: bool = False,
        extra_bwrap_args: list[str] | None = None,
    ) -> None:

        instance_config = self._read_config()

        runner = BubblejailRunner(
            parent=self,
            instance_config=instance_config,
            is_shell_debug=debug_shell,
            is_helper_debug=debug_helper_script is not None,
            is_log_dbus=debug_log_dbus,
        )
        if extra_bwrap_args:
            runner.bwrap_extra_options.extend(extra_bwrap_args)

        if debug_helper_script is not None:
            with open(debug_helper_script) as f:
                runner.helper_executable = [
                    'python', '-X', 'dev',
                    '-c', f.read(),
                ]

        if dry_run:
            runner.genetate_args()
            print('Bwrap options:')
            print(' '.join(runner.bwrap_options_args))

            print('Helper options:')
            print(' '.join(runner.helper_arguments()))

            print('Run args:')
            print(' '.join(args_to_run))

            print('Dbus session args:')
            print(' '.join(runner.dbus_proxy_args))
            return

        async with runner:
            bwrap_process = (
                await runner.create_bubblewrap_subprocess(args_to_run)
            )
            if __debug__:
                print(f"Bubblewrap started. PID: {repr(bwrap_process)}")

            task_bwrap_main = bwrap_process.wait()

            try:
                await task_bwrap_main
            except CancelledError:
                print('Bwrap cancelled')

            if bwrap_process.returncode != 0:
                raise BubblewrapRunError((
                    "Bubblewrap failed. "
                    "Try running bubblejail in terminal to see the "
                    "exact error."
                ))

            if __debug__:
                print("Bubblewrap terminated")

    async def edit_config_in_editor(self) -> None:
        # Create temporary directory
        with TemporaryDirectory() as tempdir:
            # Create path to temporary file and write exists config
            temp_file_path = Path(tempdir + 'temp.toml')
            with open(temp_file_path, mode='w') as tempfile:
                tempfile.write(self._read_config_file())

            initial_modification_time = stat(temp_file_path).st_mtime
            # Launch EDITOR on the temporary file
            run_args = [environ['EDITOR'], str(temp_file_path)]
            p = await create_subprocess_exec(*run_args)
            await p.wait()

            # If file was not modified do nothing
            if initial_modification_time >= stat(temp_file_path).st_mtime:
                print('File not modified. Not overwriting config')
                return

            # Verify that the new config is valid and save to variable
            with open(temp_file_path) as tempfile:
                new_config_toml = tempfile.read()
                BubblejailInstanceConfig(
                    cast(ServicesConfDictType, toml_loads(new_config_toml))
                )
            # Write to instance config file
            with open(self.path_config_file, mode='w') as conf_file:
                conf_file.write(new_config_toml)


class BubblejailProfile:
    def __init__(
        self,
        dot_desktop_path: str | None = None,
        is_gtk_application: bool = False,
        services:  ServicesConfDictType | None = None,
        description: str = 'No description',
        import_tips: str = 'None',
    ) -> None:
        self.dot_desktop_path = (Path(dot_desktop_path)
                                 if dot_desktop_path is not None else None)
        self.is_gtk_application = is_gtk_application
        self.config = BubblejailInstanceConfig(services)
        self.description = description
        self.import_tips = import_tips


class BubblejailInstanceMetadata:
    def __init__(
        self,
        parent: BubblejailInstance,
        creation_profile_name: str | None = None,
        desktop_entry_name: str | None = None,
    ):
        self.parent = parent
        self.creation_profile_name = creation_profile_name
        self.desktop_entry_name = desktop_entry_name

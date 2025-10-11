# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2022 igo95862
from __future__ import annotations

from asyncio import (
    CancelledError,
    open_unix_connection,
    wait_for,
)
from contextlib import AsyncExitStack
from functools import cached_property
from pathlib import Path
from sys import stderr
from tomllib import loads as toml_loads
from typing import Any, cast

from xdg.BaseDirectory import get_runtime_dir

from .bubblejail_helper import RequestRun
from .bubblejail_runner import BubblejailRunner
from .bubblejail_utils import FILE_NAME_METADATA, FILE_NAME_SERVICES
from .dbus_proxy import DBusLogEnum
from .exceptions import BubblejailException, BubblewrapRunError
from .services import ServiceContainer, ServicesConfDictType


class BubblejailInstance:

    def __init__(self, instance_home: Path):
        self.name = instance_home.stem
        # Instance directory located at $XDG_DATA_HOME/bubblejail/
        self.instance_directory = instance_home
        # If instance directory does not exists we can't do much
        # Probably someone used 'run' command before 'create'
        if not self.instance_directory.exists():
            raise BubblejailException("Instance directory does not exist")

    @cached_property
    def runtime_dir(self) -> Path:
        return Path(get_runtime_dir() + f"/bubblejail/{self.name}")

    @cached_property
    def path_config_file(self) -> Path:
        return self.instance_directory / FILE_NAME_SERVICES

    @cached_property
    def path_metadata_file(self) -> Path:
        return self.instance_directory / FILE_NAME_METADATA

    @cached_property
    def path_home_directory(self) -> Path:
        return self.instance_directory / "home"

    @cached_property
    def path_runtime_helper_dir(self) -> Path:
        """Helper run-time directory"""
        return self.runtime_dir / "helper"

    @cached_property
    def path_runtime_helper_socket(self) -> Path:
        return self.path_runtime_helper_dir / "helper.socket"

    @cached_property
    def path_runtime_dbus_session_socket(self) -> Path:
        return self.runtime_dir / "dbus_session_proxy"

    @cached_property
    def path_runtime_dbus_system_socket(self) -> Path:
        return self.runtime_dir / "dbus_system_proxy"

    def _get_metadata_dict(self) -> dict[str, Any]:
        try:
            with open(self.path_metadata_file) as metadata_file:
                return toml_loads(metadata_file.read())
        except FileNotFoundError:
            return {}

    def _save_metadata_key(self, key: str, value: Any) -> None:
        from tomli_w import dumps as toml_dumps

        toml_dict = self._get_metadata_dict()
        toml_dict[key] = value

        with open(self.path_metadata_file, mode="w") as metadata_file:
            metadata_file.write(toml_dumps(toml_dict))

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
        return self._get_metadata_value("creation_profile_name")

    @metadata_creation_profile_name.setter
    def metadata_creation_profile_name(self, profile_name: str) -> None:
        self._save_metadata_key(
            key="creation_profile_name",
            value=profile_name,
        )

    @property
    def metadata_desktop_entry_name(self) -> str | None:
        return self._get_metadata_value("desktop_entry_name")

    @metadata_desktop_entry_name.setter
    def metadata_desktop_entry_name(self, desktop_entry_name: str) -> None:
        self._save_metadata_key(
            key="desktop_entry_name",
            value=desktop_entry_name,
        )

    def read_services_file(self) -> str:
        with (self.path_config_file).open() as f:
            return f.read()

    def read_services(self, services_data: str | None = None) -> ServiceContainer:

        if services_data is None:
            services_data = self.read_services_file()

        services_dict = cast(ServicesConfDictType, toml_loads(services_data))

        return ServiceContainer(services_dict)

    def save_services(self, services: ServiceContainer) -> None:
        from tomli_w import dumps as toml_dumps

        self.save_services_file(toml_dumps(services.get_service_conf_dict()))

    def save_services_file(self, services_data: str) -> None:
        with open(self.path_config_file, mode="w") as conf_file:
            conf_file.write(services_data)

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
        log_dbus: DBusLogEnum = DBusLogEnum.NONE,
        extra_bwrap_args: list[str] | None = None,
    ) -> BubblejailRunner:

        runner = BubblejailRunner(
            parent=self,
            services_config=self.read_services(),
            is_shell_debug=debug_shell,
            is_helper_debug=debug_helper_script is not None,
            log_dbus=log_dbus,
        )
        if extra_bwrap_args:
            runner.bwrap_extra_options.extend(extra_bwrap_args)

        if debug_helper_script is not None:
            with open(debug_helper_script) as f:
                runner.helper_executable = [
                    "python",
                    "-X",
                    "dev",
                    "-c",
                    f.read(),
                ]

        if dry_run:
            runner.genetate_args()
            print("Bwrap options:", file=stderr)
            print(" ".join(runner.bwrap_options_args), file=stderr)

            print("Helper options:", file=stderr)
            print(" ".join(runner.helper_arguments()), file=stderr)

            print("Run args:", file=stderr)
            print(" ".join(args_to_run), file=stderr)

            print("D-Bus session args:", file=stderr)
            print(" ".join(runner.dbus_proxy_args), file=stderr)
            return runner

        async with AsyncExitStack() as exit_stack:
            bwrap_process = await runner.setup_runtime(exit_stack, args_to_run)
            print(f"Bubblewrap started. PID: {repr(bwrap_process)}", file=stderr)

            task_bwrap_main = bwrap_process.wait()

            try:
                await task_bwrap_main
            except CancelledError:
                print("Bwrap cancelled", file=stderr)

            if bwrap_process.returncode != 0:
                raise BubblewrapRunError(
                    (
                        "Bubblewrap failed. "
                        "Try running bubblejail in terminal to see the "
                        "exact error."
                    )
                )

            print("Bubblewrap terminated", file=stderr)
            return runner


class BubblejailProfile:
    def __init__(
        self,
        dot_desktop_path: list[str] | str | None = None,
        is_gtk_application: bool = False,
        services: ServicesConfDictType | None = None,
        description: str = "No description",
        import_tips: str = "None",
    ) -> None:

        match dot_desktop_path:
            case list():
                self.desktop_entries_paths = [Path(x) for x in dot_desktop_path]
            case str():
                self.desktop_entries_paths = [Path(dot_desktop_path)]
            case None:
                self.desktop_entries_paths = []
            case _:
                raise TypeError(
                    "Desktop entry path be a str, list[str] or None "
                    "not {dot_desktop_path!r}"
                )
        self.is_gtk_application = is_gtk_application
        self.config = ServiceContainer(services)
        self.description = description
        self.import_tips = import_tips

    def find_desktop_entry(self) -> Path | None:
        for path in self.desktop_entries_paths:
            if path.exists():
                return path

        return None


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

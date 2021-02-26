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
from __future__ import annotations

from asyncio import get_event_loop
from typing import Dict, List, Tuple

from sdbus import (DbusInterfaceCommonAsync, dbus_method_async,
                   encode_object_path, request_default_bus_name_async)

from .bubblejail_directories import BubblejailDirectories
from .services import ServiceOptionTypes, ServicesDatabase


class BubblejailManager(
        DbusInterfaceCommonAsync,
        interface_name='org.bubblejail.Manager.Unstable'):

    def __init__(self) -> None:
        super().__init__()
        self.instances: Dict[str, InstanceDbusObject] = {}
        self.create_instance_objects()

    @dbus_method_async('ssb', result_args_names=())
    async def create_instance(
            self,
            new_instance_name: str,
            profile_name: str,
            create_desktop_entry: bool) -> None:
        BubblejailDirectories.create_new_instance(
            new_instance_name, profile_name, create_desktop_entry
        )
        self.create_instance_objects()

    @dbus_method_async(
        result_signature='a(ss)',
        result_args_names=('instance_names_with_desktop_entries',)
    )
    async def list_instances_with_desktop_entries(
            self) -> List[Tuple[str, str]]:
        list_of_instances: List[Tuple[str, str]] = []

        for instance in BubblejailDirectories.iter_instances():
            desktop_entry_name = instance.metadata_desktop_entry_name
            if desktop_entry_name is None:
                desktop_entry_name = ''

            list_of_instances.append(
                (instance.name, desktop_entry_name)
            )

        return list_of_instances

    @dbus_method_async(
        result_signature='as',
        result_args_names=('list_of_profile_names',)
    )
    async def list_profiles(self) -> List[str]:
        return list(BubblejailDirectories.iter_profile_names())

    @dbus_method_async(
        result_signature='as',
        result_args_names=('list_of_services_names',)
    )
    async def list_services(self) -> List[str]:
        return list(ServicesDatabase.services_classes.keys())

    def create_instance_objects(self) -> None:

        istances_names_set = {
            instance_dir.name
            for instance_dir in
            BubblejailDirectories.iter_instances_path()
        }

        existing_instances = self.instances.keys()

        instances_to_add = istances_names_set - existing_instances
        instances_to_remove = existing_instances - istances_names_set

        for name_to_add in instances_to_add:
            self.instances[name_to_add] = InstanceDbusObject(name_to_add)

        for name_to_remove in instances_to_remove:
            self.instances.pop(name_to_remove)


class InstanceDbusObject(
        DbusInterfaceCommonAsync,
        interface_name='org.bubblejail.Instance.Unstable'):

    def __init__(self, instance_name: str):
        super().__init__()
        self.services: Dict[str, ServiceDbusObject] = {}

        self.the_instance = BubblejailDirectories.instance_get(instance_name)
        self.instance_config = self.the_instance._read_config()
        self.dbus_path = encode_object_path(
            '/org/bubblejail/instance', instance_name)
        self.export_to_dbus(self.dbus_path)

        self.update_options()

    @dbus_method_async('s')
    async def enable_service(self, service_name: str) -> None:
        self.instance_config.enable_service(service_name)

        self.update_options()

    @dbus_method_async('s')
    async def disable_service(self, service_name: str) -> None:
        self.instance_config.disable_service(service_name)

        self.update_options()

    @dbus_method_async()
    async def save(self) -> None:
        ...

    def update_options(self) -> None:
        current_services = self.services.keys()
        actual_services = self.instance_config.services_dicts.keys()

        services_to_add = actual_services - current_services
        services_to_remove = current_services - actual_services

        for name_to_add in services_to_add:
            self.services[name_to_add] = ServiceDbusObject(
                self.dbus_path, name_to_add)

        for name_to_remove in services_to_remove:
            self.services.pop(name_to_remove)


class ServiceDbusObject(
        DbusInterfaceCommonAsync,
        interface_name='org.bubblejail.Service.Unstable'):

    def __init__(self, parent_path: str, service_name: str):
        super().__init__()
        self.export_to_dbus(
            encode_object_path(parent_path + "/service", service_name)
        )

    @dbus_method_async('sv')
    async def set_option(
            self,
            option_name: str,
            option_value: ServiceOptionTypes) -> None:
        ...

    @dbus_method_async(result_signature='v')
    async def get_option(self) -> ServiceOptionTypes:
        ...


manager = BubblejailManager()


loop = get_event_loop()


def startup() -> None:
    manager.export_to_dbus('/org/bubblejail/manager')
    loop.create_task(
        request_default_bus_name_async('org.bubblejail.Manager'))
    loop.run_forever()


if __name__ == '__main__':
    startup()

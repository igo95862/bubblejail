# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 igo95862
from __future__ import annotations

from .bubblejail_instance import BubblejailInstance
from .dbus_proxy import DBusProxyLogParser
from .services import CommonSettings, ServiceContainer


class DBusWizard:

    def __init__(
        self, instance: BubblejailInstance, dbus_log: DBusProxyLogParser
    ) -> None:
        self.instance = instance
        self.dbus_log = dbus_log
        self.changed = False

    def run(self) -> None:
        services_config = self.instance.read_services()

        self.handle_dbus_name_owner(services_config)

        if self.changed:
            self.instance.save_services(services_config)
            print("Services config updated.")
        else:
            print("No changes to services configuration.")

    def handle_dbus_name_owner(self, services_config: ServiceContainer) -> None:
        try:
            common_settings = services_config.context.get_settings(
                CommonSettings.Settings
            )
        except KeyError:
            common_settings = CommonSettings.Settings()
            services_config.service_settings[CommonSettings.name] = common_settings
            services_config.service_settings_to_type[CommonSettings.Settings] = (
                common_settings
            )

        if common_settings.dbus_name:
            print(
                "Skipping setting D-Bus name owner because it is "
                f"already set to {common_settings.dbus_name!r}."
            )
            return

        print("Checking owned D-Bus names.")

        wants_own_name = self.dbus_log.wants_own_first_name
        if not wants_own_name:
            print("Sandboxed application did not try own any D-Bus names.")
            return

        print(f"Sandboxed application tried to acquire {wants_own_name!r} D-Bus name.")

        if (
            input(f"Set owned D-Bus name to {wants_own_name!r}? [y/N]: ")
            .strip()
            .lower()
            == "y"
        ):
            common_settings.dbus_name = wants_own_name
            self.changed = True
            print(
                f"Sandbox instance is now allowed to own {wants_own_name!r} D-Bus name."
            )
        else:
            print("Skipped setting owned D-Bus name.")

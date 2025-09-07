# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
from __future__ import annotations

from dataclasses import fields
from tomllib import loads as toml_loads
from unittest import TestCase
from unittest import main as unittest_main

from bubblejail.exceptions import ServiceConflictError
from bubblejail.services import (
    SERVICES_CLASSES,
    SERVICES_MAP,
    X11,
    BubblejailDefaults,
    BubblejailService,
    EmptySettings,
    ServiceContainer,
    ServicesConfig,
)


class TestServices(TestCase):

    def test_x11_socket_bind(self) -> None:
        correct_path = "/tmp/.X11-unix/X0"

        self.assertEqual(
            X11.x11_socket_path(":0"),
            correct_path,
        )

        self.assertEqual(
            X11.x11_socket_path("unix/:0"),
            correct_path,
        )

        self.assertEqual(
            X11.x11_socket_path(":0.1"),
            correct_path,
        )

        self.assertEqual(
            X11.x11_socket_path("unix/:1"),
            "/tmp/.X11-unix/X1",
        )

        self.assertIsNone(X11.x11_socket_path("tcp/localhost:1"))

        self.assertIsNone(X11.x11_socket_path("unix/localhost:1"))

    def test_service_conflict_relationship(self) -> None:
        # Test that conflict points to existing service
        # and reverse relationship exists
        for service in SERVICES_CLASSES:
            for conflict in service.conflicts:
                conflict_service = SERVICES_MAP[conflict]
                self.assertIn(
                    service.name,
                    conflict_service.conflicts,
                    msg=(
                        f"Reverse conflict of {service.name} "
                        f"to {conflict_service.name} not found"
                    ),
                )

    def test_service_conflict_load(self) -> None:
        test_conflict_config_str = """[ibus]
[fcitx]
"""
        test_conflict_config = toml_loads(test_conflict_config_str)
        with self.assertRaises(ServiceConflictError):
            ServiceContainer(test_conflict_config)

        test_good_config_str = """[ibus]
[x11]
"""
        test_good_config = toml_loads(test_good_config_str)
        ServiceContainer(test_good_config)

    def test_services_classes(self) -> None:
        for subcls in BubblejailService.__subclasses__():
            if subcls is BubblejailDefaults:
                continue

            self.assertIn(subcls, SERVICES_CLASSES)

        for service in SERVICES_CLASSES:
            if not service.Settings is EmptySettings:
                self.assertEqual(
                    f"{service.__name__}Settings",
                    service.Settings.__name__,
                )

    def test_services_config(self) -> None:
        key_to_type_str = {f.name: f.type for f in fields(ServicesConfig)}

        for service in SERVICES_CLASSES:
            self.assertIn(service.name, key_to_type_str)
            self.assertEqual(
                (
                    "EmptySettings | None"
                    if service.Settings is EmptySettings
                    else f"{service.__name__}Settings | None"
                ),
                key_to_type_str[service.name],
            )


if __name__ == "__main__":
    unittest_main()

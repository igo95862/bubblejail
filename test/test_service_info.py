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

from unittest import TestCase
from unittest import main as unittest_main

try:
    from tomllib import loads as toml_loads
except ImportError:
    from tomli import loads as toml_loads

from bubblejail.exceptions import ServiceConflictError
from bubblejail.services import (
    SERVICES_CLASSES,
    SERVICES_MAP,
    X11,
    ServiceContainer,
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

        self.assertIsNone(
            X11.x11_socket_path("tcp/localhost:1")
        )

        self.assertIsNone(
            X11.x11_socket_path("unix/localhost:1")
        )

    def test_service_conflict_relationship(self) -> None:
        # Test that conflict points to existing service
        # and reverse relationship exists
        for service in SERVICES_CLASSES:
            for conflict in service.conflicts:
                conflict_service = SERVICES_MAP[conflict]
                self.assertIn(
                    service.name, conflict_service.conflicts,
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


if __name__ == '__main__':
    unittest_main()

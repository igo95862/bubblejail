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

from functools import partialmethod
from typing import Type, get_type_hints
from unittest import TestCase, expectedFailure
from unittest import main as unittest_main

from bubblejail.services import SERVICES, BubblejailService


def test_service_info(
        self: TestCase,
        service: Type[BubblejailService]) -> None:

    self.assertIsNotNone(service.info, f"Service {service} info is None")

    service_init_types = get_type_hints(service.__init__)

    # Compare keys
    self.assertEqual(
        set(service_init_types.keys()),
        set(service.info.options.keys()),
        f"Info and init options of service {service} do not match",
    )

    for option_name, option_info in service.info.options.items():
        self.assertIs(
            option_info.typing,
            service_init_types[option_name],
            (
                "Type mismatch, "
                f"expected {service_init_types[option_name]}, "
                f"got {option_info.typing}"
            )

        )


class TestDefaultServiceFailure(TestCase):
    @expectedFailure
    def test_default_failure(self) -> None:
        test_service_info(self, SERVICES['default'])


# Create classes to test services
for service_name, service_class in SERVICES.items():
    # Defalt service has special options
    # that are not supposed to be edited by user
    if service_name == 'default':
        continue

    vars()[service_name] = type(
        f"Test_{service_name}",
        (TestCase, ),
        {
            'test_service_info': partialmethod(
                test_service_info, service_class)
        }

    )

if __name__ == '__main__':
    unittest_main()

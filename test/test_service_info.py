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

from typing import Dict, List, get_type_hints
from unittest import TestCase
from unittest import main as unittest_main

from bubblejail.services import (
    SERVICES_CLASSES,
    BubblejailService,
    ServiceOption,
)

argless_dict = {'return': type(None)}


class TestServices(TestCase):

    def setUp(self) -> None:
        self.services: List[BubblejailService] = [
            x() for x in SERVICES_CLASSES
        ]

    def test_service_options(self) -> None:
        for service in self.services:
            with self.subTest(f"Service: {service.pretty_name}"):
                service_init_types = get_type_hints(service.__class__.__init__)

                if service_init_types == argless_dict:
                    service_init_types = {}

                service_options: Dict[str, ServiceOption] = {
                    option.name: option for option in service.iter_options()
                }

                with self.subTest((f"Service {service.pretty_name}:"
                                   "compare init args and option names")):
                    service_option_names = set(service_options.keys())
                    service_init_args_name = set(service_init_types.keys())

                    self.assertEqual(
                        first=service_option_names,
                        second=service_init_args_name,
                        msg=(f"Options: {service_option_names},"
                             f" Init: {service_init_args_name}"),
                    )

                with self.subTest((f"Service {service.pretty_name}:"
                                   "compare init args and option types")):
                    # TODO: implement
                    ...

    def test_not_enabled_no_yields(self) -> None:
        for service in self.services:
            with self.subTest(f"Service: {service.pretty_name}"):
                service.enabled = False
                should_be_empty = list(service)

                self.assertFalse(should_be_empty)


if __name__ == '__main__':
    unittest_main()

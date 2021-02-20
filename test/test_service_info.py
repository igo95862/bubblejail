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


from unittest import TestCase
from unittest import main as unittest_main

from bubblejail.exceptions import (ServiceOptionUnknownError,
                                   ServiceOptionWrongTypeError,
                                   ServiceUnknownError)
from bubblejail.services import MultipleServicesOptionsType, ServicesConfig

wrong_service_dict: MultipleServicesOptionsType = {
    'bad_service': {
        'some_option': 'asdas',
    }
}

wrong_option_dict: MultipleServicesOptionsType = {
    'common': {
        'some_option': 'asdas',
    }
}

wrong_option_type_dict: MultipleServicesOptionsType = {
    'common': {
        'share_local_time': 'Test',
    }
}

correct_dict: MultipleServicesOptionsType = {
    'common': {
        'share_local_time': True,
    }
}


class TestServices(TestCase):

    def test_service_wrong_option(self) -> None:
        self.assertRaises(
            ServiceUnknownError,
            lambda: ServicesConfig(wrong_service_dict))

        self.assertRaises(
            ServiceOptionUnknownError,
            lambda: ServicesConfig(wrong_option_dict)
        )

        self.assertRaises(
            ServiceOptionWrongTypeError,
            lambda: ServicesConfig(wrong_option_type_dict)
        )

    def test_service_manipulation(self) -> None:
        test_dict = correct_dict.copy()

        test_config = ServicesConfig(test_dict)

        test_config.set_service_option('common', 'share_local_time', False)

        def wrong_type() -> None:
            test_config.set_service_option(
                'common', 'share_local_time', 'asdasd')

        self.assertRaises(ServiceOptionWrongTypeError, wrong_type)

        def wrong_service() -> None:
            test_config.enable_service('asdasdasd')

        self.assertRaises(ServiceUnknownError, wrong_service)

        self.assertNotIn('direct_rendering', test_config.services_dicts)

        test_config.enable_service('direct_rendering')

        self.assertIn('direct_rendering', test_config.services_dicts)

        test_config.set_service_option('direct_rendering', 'enable_aco', True)

        self.assertEqual(
            True,
            test_config.get_service_option('direct_rendering', 'enable_aco'))

        test_config.disable_service('direct_rendering')

        self.assertNotIn('direct_rendering', test_config.services_dicts)


if __name__ == '__main__':
    unittest_main()

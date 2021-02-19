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


if __name__ == '__main__':
    unittest_main()

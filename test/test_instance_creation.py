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


from os import environ
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest import main as unittest_main

from bubblejail.bubblejail_directories import BubblejailDirectories
from bubblejail.bubblejail_instance import BubblejailInstance
from bubblejail.bubblejail_utils import FILE_NAME_SERVICES


class TestInstanceGeneration(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """Set up temporary directory for tests"""
        self.dir = TemporaryDirectory()
        self.dir_path = Path(self.dir.name)
        self.data_directory = self.dir_path / 'data'
        self.data_directory.mkdir()
        environ['BUBBLEJAIL_DATADIRS'] = str(self.data_directory)

    async def test_empty_profile(self) -> None:
        instance_name = 'test_instance_no_profile'

        new_instance = BubblejailDirectories.create_new_instance(
            new_name=instance_name,
            profile_name=None,
            create_dot_desktop=False,
        )

        await self._instance_common_test(new_instance)

    def tearDown(self) -> None:
        self.dir.cleanup()

    async def _instance_common_test(self, instance: BubblejailInstance
                                    ) -> None:
        instance_dir = instance.instance_directory
        self.assertTrue(instance_dir.exists())
        self.assertTrue(instance_dir.is_dir())
        self.assertTrue((instance_dir / FILE_NAME_SERVICES).exists())
        self.assertTrue((instance_dir / 'home').exists())

        await instance.async_run_init([], dry_run=True)


if __name__ == '__main__':
    unittest_main()

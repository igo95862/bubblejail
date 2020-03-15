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


from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest import main as unittest_main
from unittest import skipUnless

from bubblejail.bubblejail_instance import BubblejailInstance
from bubblejail.bubblejail_utils import BubblejailProfile
from toml import load as toml_load

# TODO: needs to be improved


class TestInstanceGeneration(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """Set up temporary directory for tests"""
        self.dir = TemporaryDirectory()
        self.dir_path = Path(self.dir.name)
        self.data_directory = self.dir_path / 'data'
        self.data_directory.mkdir()
        BubblejailInstance.DATA_DIR = self.data_directory
        BubblejailInstance.DESKTOP_ENTRIES_DIR = self.dir_path

    @skipUnless(
        Path('/usr/share/applications/firefox.desktop').exists(),
        'Firefox not installed'
    )
    async def test_create_firefox(self) -> None:
        instance_name = 'test_instance'

        with open('./bubblejail/profiles/firefox.toml') as f:
            profile = BubblejailProfile(**toml_load(f))

        new_instance = await BubblejailInstance.create_new(
            new_name=instance_name,
            profile=profile,
            create_dot_desktop=True,
        )

        instance_dir = new_instance.instance_directory
        self.assertTrue(instance_dir.exists())
        self.assertTrue(instance_dir.is_dir())
        self.assertTrue((instance_dir / 'config.toml').exists())
        self.assertTrue((instance_dir / 'home').exists())

    async def test_empty_profile(self) -> None:
        instance_name = 'test_instance_no_profile'
        profile = BubblejailProfile()

        new_instance = await BubblejailInstance.create_new(
            new_name=instance_name,
            profile=profile,
            create_dot_desktop=True,
        )
        instance_dir = new_instance.instance_directory
        self.assertTrue(instance_dir.exists())
        self.assertTrue(instance_dir.is_dir())
        self.assertTrue((instance_dir / 'config.toml').exists())
        self.assertTrue((instance_dir / 'home').exists())

    def tearDown(self) -> None:
        self.dir.cleanup()


if __name__ == '__main__':
    unittest_main()

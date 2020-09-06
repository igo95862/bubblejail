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
from unittest import TestCase
from unittest import main as unittest_main


from bubblejail.bubblejail_instance import BubblejailProfile
from toml import load


class TestProfiles(TestCase):
    def test_profiles(self) -> None:
        for profile_path in Path('./bubblejail/profiles/').iterdir():
            with self.subTest(profile_path.stem):
                BubblejailProfile(**load(profile_path))


if __name__ == '__main__':
    unittest_main()

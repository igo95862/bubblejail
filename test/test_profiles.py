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
from toml import load
from bubblejail.bubblejail_utils import BubblejailProfile


class TestProfiles(TestCase):
    """Iterates over all provided profiles and tries to generate args"""

    def test_profiles(self) -> None:
        for profile_toml in Path('./bubblejail/profiles/').iterdir():
            with open(profile_toml) as f:
                profile_dict = load(f)

            with self.subTest(profile_toml):
                p = BubblejailProfile(**profile_dict)
                conf = p.get_config()

                for s in conf.iter_services():
                    for _ in s:
                        ...


if __name__ == '__main__':
    unittest_main()

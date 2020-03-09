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
from pathlib import Path
from typing import Any, Dict
from unittest import SkipTest, TestCase
from unittest import main as unittest_main

from bubblejail.bubblejail_utils import BubblejailProfile
from bubblejail.exceptions import ServiceUnavalibleError
from toml import load

for profile_toml in Path('./bubblejail/profiles/').iterdir():
    with open(profile_toml) as f:
        profile_dict = load(f)

    def test_profile(self: TestCase, profile: Dict[Any, Any]) -> None:
        p = BubblejailProfile(**profile)
        conf = p.get_config()
        try:
            conf.verify()
        except ServiceUnavalibleError:
            raise SkipTest(
                f"Profile non-initializable on local machine: "
                f"{self}"
            )

    vars()[profile_toml.stem] = type(
        profile_toml.stem,
        (TestCase, ),
        {
            'test_profile': partialmethod(test_profile, profile=profile_dict),
        }
    )


if __name__ == '__main__':
    unittest_main()

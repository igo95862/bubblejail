# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
from __future__ import annotations

from pathlib import Path
from tomllib import load as toml_load
from unittest import TestCase
from unittest import main as unittest_main

from bubblejail.bubblejail_instance import BubblejailProfile


PROJECT_ROOT_PATH = Path(__file__).parent.parent


class TestProfiles(TestCase):
    def test_profiles(self) -> None:
        profiles_str_path = (
            PROJECT_ROOT_PATH / 'data/usr-share/bubblejail/profiles'
        )

        for profile_path in profiles_str_path.iterdir():
            with self.subTest(profile_path.stem):
                with open(profile_path, mode='rb') as f:
                    BubblejailProfile(**toml_load(f))


if __name__ == '__main__':
    unittest_main()

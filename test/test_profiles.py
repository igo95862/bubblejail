# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
from __future__ import annotations

from os import environ
from pathlib import Path
from unittest import TestCase
from unittest import main as unittest_main

try:
    from tomllib import load as toml_load
except ImportError:
    from tomli import load as toml_load  # type: ignore

from bubblejail.bubblejail_instance import BubblejailProfile


class TestProfiles(TestCase):
    def test_profiles(self) -> None:
        meson_source_root = Path(environ['MESON_SOURCE_ROOT'])
        profiles_str_path = (
            meson_source_root / 'data/usr-share/bubblejail/profiles'
        )

        for profile_path in profiles_str_path.iterdir():
            with self.subTest(profile_path.stem):
                with open(profile_path, mode='rb') as f:
                    BubblejailProfile(**toml_load(f))


if __name__ == '__main__':
    unittest_main()

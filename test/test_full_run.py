# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2023 igo95862

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

from os import environ
from pathlib import Path
from random import sample
from string import ascii_letters
from subprocess import run as subprocess_run
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from unittest import IsolatedAsyncioTestCase
from unittest import main as unittest_main
from unittest.mock import MagicMock

from bubblejail import bubblejail_directories
from bubblejail.bubblejail_directories import BubblejailDirectories

if TYPE_CHECKING:
    from collections.abc import Generator

test_profile = """
description = "testing profile"

[services.root_share]
paths = ["{shared_path}"]
"""


class TestFullRun(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory(
            prefix="bubblejail_test_dir",
        )
        self.temp_dir_path = Path(self.temp_dir.name)

        self.temp_shared_dir = TemporaryDirectory(
            prefix="bubblejail_test_shared_dir",
        )
        self.temp_shared_dir_path = Path(self.temp_shared_dir.name)

        self.data_dir = self.temp_dir_path / "data"
        self.data_dir.mkdir()
        self.bubblejail_data_dir = self.data_dir / "bubblejail"

        self.profile_dir = self.temp_dir_path / "profiles"
        self.profile_dir.mkdir()

        self.run_dir = self.temp_dir_path / "run"
        self.run_dir.mkdir()
        environ["XDG_RUNTIME_DIR"] = str(self.run_dir)
        environ["DBUS_SESSION_BUS_ADDRESS"] = str(self.run_dir / "test.socker")

        self.test_profile_name = "".join(sample(ascii_letters, 10))
        self.test_profile_path = (
            self.profile_dir / self.test_profile_name
        ).with_suffix(".toml")
        with open(self.test_profile_path, mode="x") as f:
            f.write(test_profile.format(shared_path=self.temp_shared_dir_path))

        setattr(
            bubblejail_directories,
            "xdg_data_home",
            str(self.data_dir),
        )

        def custom_profile_dirs() -> Generator[Path, None, None]:
            yield self.profile_dir

        setattr(
            BubblejailDirectories,
            "iter_profile_directories",
            custom_profile_dirs,
        )

        setattr(
            BubblejailDirectories,
            "update_mime_database",
            MagicMock(),
        )

        self.test_instance_name = "".join(sample(ascii_letters, 12))

    async def test_full_run(self) -> None:
        # Create
        self.assertFalse(self.bubblejail_data_dir.exists())
        BubblejailDirectories.create_new_instance(
            self.test_instance_name,
            profile_name=self.test_profile_name,
            create_dot_desktop=True,
        )
        self.assertTrue(self.bubblejail_data_dir.exists())

        with self.subTest("Validate desktop entry"):
            for desktop_entry_file in (
                self.data_dir / "applications"
            ).iterdir():
                subprocess_run(
                    ("desktop-file-validate", str(desktop_entry_file)),
                    check=True,
                )

        instance = BubblejailDirectories.instance_get(self.test_instance_name)
        test_file_path = self.temp_shared_dir_path / "id.txt"
        self.assertFalse(test_file_path.exists())
        with self.subTest("Dry-run"):
            await instance.async_run_init(
                [
                    "sh",
                    "-ceu",
                    f"id > {test_file_path}",
                ],
                dry_run=True,
            )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        self.temp_shared_dir.cleanup()


if __name__ == "__main__":
    unittest_main()

# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019-2022 igo95862

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

from pathlib import Path
from subprocess import run as subprocess_run
from os import isatty
from sys import stdin


class HomeDirectoryPlugin:
    def __init__(self, home_directory: Path, plugin_directory: Path):
        self.home_directory = home_directory
        self.plugin_directory = plugin_directory

    @classmethod
    def create(cls, plugin_directory: Path) -> None:
        raise NotImplementedError

    def enter(self) -> None:
        raise NotImplementedError

    def exit(self) -> None:
        raise NotImplementedError


class GocryptfsHome(HomeDirectoryPlugin):
    @classmethod
    def create(cls, plugin_directory: Path) -> None:
        cipher_directory = plugin_directory / 'cipher'
        cipher_directory.mkdir(mode=0o700)

        subprocess_run(
            args=('gocryptfs', '-init', cipher_directory),
            check=True,
        )

    def enter(self) -> None:
        if not isatty(stdin.fileno()):
            raise RuntimeError(
                'Can\'t enter Gocryptfs password.'
                'Not connected to terminal'
            )

        cipher_directory = self.plugin_directory / 'cipher'

        subprocess_run(
            args=('gocryptfs', cipher_directory, self.home_directory),
            check=True,
        )

    def exit(self) -> None:
        subprocess_run(
            args=('umount', self.home_directory),
            check=True,
        )


HOME_PLUGINS = {
    'gocryptfs_home': GocryptfsHome,
}

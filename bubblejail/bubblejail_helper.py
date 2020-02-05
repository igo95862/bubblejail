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

from asyncio import (StreamReader, StreamWriter, create_task,
                     open_unix_connection)
from asyncio import run as async_run
from os import _exit
from pathlib import Path
from typing import Optional


class BubblejailHelper:
    def __init__(
            self, helper_socket_path: Path = Path('/tmp/bubble_sock')):
        self.helper_socket_path = helper_socket_path
        if not helper_socket_path.exists():
            print('Did not find helper socket')
            _exit(1)

        self.helper_in: Optional[StreamReader] = None
        self.helper_out: Optional[StreamWriter] = None

    async def helper_input(self) -> None:
        if self.helper_in is None:
            raise TypeError()

        while True:
            line = self.helper_in.readline()
            if not line:
                return

    async def helper_main(self) -> None:
        (helper_in, helper_out) = await open_unix_connection(
            path=self.helper_socket_path)

        self.helper_in = helper_in
        self.helper_out = helper_out

        input_task = create_task(self.helper_input())
        await input_task


async_run(BubblejailHelper().helper_main())

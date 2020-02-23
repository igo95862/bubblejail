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

from asyncio import (StreamReader, StreamWriter, get_event_loop,
                     open_unix_connection, create_task)
from os import unlink
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest import main as unittest_main

from bubblejail.bubblejail_helper import BubblejailHelper, RequestPing

# Test socket needs to be cleaned up
test_socket_path = Path('./test_socket')


class HelperTests(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        # Set asyncio debug mode
        self.event_loop = get_event_loop()
        self.event_loop.set_debug(True)
        # Create helper
        self.helper = BubblejailHelper(
            helper_socket_path=test_socket_path,
            no_child_timeout=None,
            use_fixups=False,
            exec_argv=False,
        )

    async def asyncSetUp(self) -> None:
        # Start helper
        await self.helper.start_async()
        # Get stream reader and writter
        (reader, writter) = await open_unix_connection(
            path=test_socket_path,
        )
        self.reader: StreamReader = reader
        self.writter: StreamWriter = writter

    async def test_ping(self) -> None:
        ping_request = RequestPing('test')
        self.writter.write(ping_request.to_json_byte_line())
        await self.writter.drain()

        response = await self.reader.readline()

        print('Response bytes:', response)
        self.assertIn(b'pong', response, 'No pong in response')

    async def asyncTearDown(self) -> None:
        create_task(self.helper.stop_async())
        await self.helper
        # Cleanup socket
        unlink(test_socket_path)
        # Close the reader and writter
        self.writter.close()
        await self.writter.wait_closed()


if __name__ == '__main__':
    unittest_main()

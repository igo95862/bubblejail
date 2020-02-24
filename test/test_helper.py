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

from asyncio import (StreamReader, StreamWriter, create_task, get_event_loop,
                     open_unix_connection)
from os import unlink
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest import main as unittest_main

from bubblejail.bubblejail_helper import (BubblejailHelper, RequestPing,
                                          get_helper_argument_parser)

# Test socket needs to be cleaned up
test_socket_path = Path('./test_socket')


class HelperTests(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        # Set asyncio debug mode
        self.event_loop = get_event_loop()
        self.event_loop.set_debug(True)
        # Create helper
        self.helper = BubblejailHelper(
            startup_args=[],
            helper_socket_path=test_socket_path,
            no_child_timeout=None,
            use_fixups=False,
        )
        self.parser = get_helper_argument_parser()

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

    def test_argument_parser_no_shell(self) -> None:
        no_shell_example_args = [
            '/bin/true',
            '--long-opt', '-e', '-test',
            '/bin/false', '--shell'
        ]
        parsed_args = self.parser.parse_args(no_shell_example_args)

        self.assertFalse(parsed_args.shell)
        self.assertEqual(parsed_args.args_to_run, no_shell_example_args)

    def test_argument_parser_with_shell(self) -> None:
        with_shell_example_args = [
            '--shell', '/bin/ls', '-l'
        ]

        parsed_args = self.parser.parse_args(with_shell_example_args)

        self.assertTrue(parsed_args.shell)
        self.assertEqual(
            parsed_args.args_to_run, with_shell_example_args[1:])

    def test_argument_parser_just_shell(self) -> None:
        just_shell_example = [
            '--shell'
        ]

        parsed_args = self.parser.parse_args(just_shell_example)

        self.assertTrue(parsed_args.shell)
        self.assertEqual(parsed_args.args_to_run, [])

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

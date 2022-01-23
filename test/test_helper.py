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

from asyncio import (StreamReader, StreamWriter, create_subprocess_exec,
                     create_task, get_running_loop, open_unix_connection)
from os import unlink
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest import main as unittest_main

from bubblejail.bubblejail_helper import (BubblejailHelper, RequestPing,
                                          get_helper_argument_parser)

# Test socket needs to be cleaned up
test_socket_path = Path('./test_socket')


class HelperTests(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        # Create helper
        self.helper = BubblejailHelper(
            startup_args=[],
            helper_socket_path=test_socket_path,
            no_child_timeout=None,
            use_fixups=False,
        )

    async def asyncSetUp(self) -> None:
        # Set asyncio debug mode
        get_running_loop().set_debug(True)
        # Start helper
        await self.helper.start_async()
        # Get stream reader and writer
        (reader, writer) = await open_unix_connection(
            path=test_socket_path,
        )
        self.reader: StreamReader = reader
        self.writer: StreamWriter = writer

    async def test_ping(self) -> None:
        """Test pinging helper over unix socket"""
        ping_request = RequestPing('test')
        self.writer.write(ping_request.to_json_byte_line())
        await self.writer.drain()

        response = await self.reader.readline()

        print('Response bytes:', response)
        self.assertIn(b'pong', response, 'No pong in response')

    async def asyncTearDown(self) -> None:
        create_task(self.helper.stop_async())
        await self.helper
        # Cleanup socket
        unlink(test_socket_path)
        # Close the reader and writer
        self.writer.close()
        await self.writer.wait_closed()


class HelperParserTests(TestCase):
    def setUp(self) -> None:
        self.parser = get_helper_argument_parser()

    def test_parser(self) -> None:
        """Test how helper argument parser works"""
        with self.subTest('No shell'):
            no_shell_example_args = [
                '/bin/true',
                '--long-opt', '-e', '-test',
                '/bin/false', '--shell'
            ]
            parsed_args = self.parser.parse_args(no_shell_example_args)

            self.assertFalse(parsed_args.shell)
            self.assertEqual(parsed_args.args_to_run, no_shell_example_args)

        with self.subTest('Shell plus args'):
            with_shell_example_args = [
                '--shell', '/bin/ls', '-l'
            ]

            parsed_args = self.parser.parse_args(with_shell_example_args)

            self.assertTrue(parsed_args.shell)
            self.assertEqual(
                parsed_args.args_to_run, with_shell_example_args[1:])

        with self.subTest('Only shell'):
            just_shell_example = [
                '--shell'
            ]

            parsed_args = self.parser.parse_args(just_shell_example)

            self.assertTrue(parsed_args.shell)
            self.assertEqual(parsed_args.args_to_run, [])


class PidTrackerTest(IsolatedAsyncioTestCase):

    async def test_process_detection(self) -> None:
        """Test process detection"""

        with self.subTest('PID tracking: no child of this process'):
            self.assertFalse(BubblejailHelper.process_has_child())

        child_process = await create_subprocess_exec(
            'sleep', '1d',
        )

        with self.subTest('PID tracking: has child method'):
            self.assertTrue(
                BubblejailHelper.process_has_child())

        with self.subTest('PID tracking by command: right command'):
            # WARN: This will give false positive if you have
            # sleep runing anywhere on the system
            # Maybein the future we can setup quick pid namespace
            self.assertTrue(
                BubblejailHelper.proc_has_process_command('sleep'))

        with self.subTest('PID tracking by command: wrong command'):
            self.assertFalse(
                BubblejailHelper.proc_has_process_command(
                    'asdjhaikefrasendiklfnsmzkjledf'))

        # Cleanup
        child_process.terminate()
        await child_process.wait()


if __name__ == '__main__':
    unittest_main()

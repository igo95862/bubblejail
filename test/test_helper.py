# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
from __future__ import annotations

from asyncio import (
    StreamReader,
    StreamWriter,
    create_subprocess_exec,
    create_task,
    get_running_loop,
    open_unix_connection,
)
from pathlib import Path
from socket import AF_UNIX, socket
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest import main as unittest_main

from bubblejail.bubblejail_helper import (
    BubblejailHelper,
    RequestPing,
    get_helper_argument_parser,
)


class HelperTests(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        # Create helper
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_dir_path = Path(self.temp_dir.name)
        self.test_socket_path = self.temp_dir_path / 'test_socket'

        self.test_socket = socket(AF_UNIX)
        self.test_socket.bind(bytes(self.test_socket_path))
        self.helper = BubblejailHelper(
            self.test_socket,
            startup_args=[],
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
            path=self.test_socket_path,
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
        # Close the reader and writer
        self.writer.close()
        await self.writer.wait_closed()


class HelperParserTests(TestCase):
    def setUp(self) -> None:
        self.parser = get_helper_argument_parser()

    def test_parser(self) -> None:
        """Test how helper argument parser works"""
        required_args = ['--helper-socket', '0', '--']

        with self.subTest('No shell'):
            no_shell_example_args = [
                '/bin/true',
                '--long-opt', '-e', '-test',
                '/bin/false', '--shell',
            ]
            parsed_args = self.parser.parse_args(
                required_args + no_shell_example_args
            )

            self.assertFalse(parsed_args.shell)
            self.assertEqual(parsed_args.args_to_run, no_shell_example_args)

        with self.subTest('Shell plus args'):
            with_shell_example_args = [
                 '/bin/ls', '-l'
            ]

            parsed_args = self.parser.parse_args(
                ['--shell'] + required_args + with_shell_example_args
            )

            self.assertTrue(parsed_args.shell)
            self.assertEqual(
                parsed_args.args_to_run, with_shell_example_args)

        with self.subTest('Only shell'):
            parsed_args = self.parser.parse_args(
                ['--shell'] + required_args
            )

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
            # sleep running anywhere on the system
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

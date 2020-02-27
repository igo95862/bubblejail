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

from argparse import REMAINDER as ARG_REMAINDER
from argparse import ArgumentParser
from asyncio import (AbstractServer, CancelledError, Event, StreamReader,
                     StreamWriter, Task, create_subprocess_exec, create_task)
from asyncio import run as async_run
from asyncio import sleep, start_unix_server
from asyncio.subprocess import DEVNULL, PIPE, STDOUT
from json import dumps as json_dumps
from json import loads as json_loads
from pathlib import Path
from typing import (Any, Awaitable, Dict, Generator, List, Literal, Optional,
                    Union)

from xdg.BaseDirectory import get_runtime_dir

# region Rpc
RpcMethods = Literal['ping', 'run']
RpcData = Union[Dict[str, Union[str, List[str]]], List[str]]
RpcType = Dict[str, Optional[Union[str, RpcData, RpcMethods]]]


class JsonRpcRequest:
    @staticmethod
    def _dict_to_json_byte_line(rpc_dict: Dict[Any, Any]) -> bytes:
        string_form = json_dumps(rpc_dict) + '\n'
        return string_form.encode()

    @staticmethod
    def _json_byte_line_to_dict(data: bytes) -> Dict[Any, Any]:
        decoded_dict: Dict[Any, Any] = json_loads(data)
        # Replace 'id' with 'request_id'
        decoded_dict['request_id'] = decoded_dict['id']
        decoded_dict.pop('id')

        return decoded_dict

    def __init__(self,
                 method: RpcMethods,
                 request_id: Optional[str] = None,
                 params: Optional[RpcData] = None,
                 ):
        self.request_id = request_id
        self.method = method
        self.params = params

    def to_json_byte_line(self) -> bytes:
        dict_form = {
            "id": self.request_id,
            "method": self.method,
            "params": self.params,
        }
        return self._dict_to_json_byte_line(dict_form)

    def _get_reponse_bytes(self, rpc_data: RpcData) -> bytes:
        response_dict = {
            "id": self.request_id,
            "result": rpc_data,
        }
        return self._dict_to_json_byte_line(response_dict)


class RequestPing(JsonRpcRequest):
    def __init__(self, request_id: Optional[str] = None) -> None:
        super().__init__(
            method='ping',
            request_id=request_id,
        )

    def response_ping(self) -> bytes:
        return self._get_reponse_bytes(['pong'])


class RequestRun(JsonRpcRequest):
    def __init__(
        self,
        args_to_run: List[str],
        request_id: Optional[str] = None
    ) -> None:
        super().__init__(
            method='run',
            request_id=request_id,
            params=args_to_run,
        )
        self.args_to_run = args_to_run

    def response_run(self, text: str) -> bytes:
        return self._get_reponse_bytes({'return': text})


RpcRequests = Union[RequestPing, RequestRun]


def request_selector(data: bytes) -> RpcRequests:
    decoded_dict = JsonRpcRequest._json_byte_line_to_dict(data)

    method = decoded_dict['method']
    request_id = decoded_dict['request_id']
    params = decoded_dict['params']

    if method == 'ping':
        return RequestPing(request_id=request_id)
    elif method == 'run':
        return RequestRun(
            request_id=request_id,
            args_to_run=params,
        )
    else:
        raise TypeError('Unknown rpc method.')
# endregion Rpc


class BubblejailHelper(Awaitable[bool]):
    def __init__(
        self,
            startup_args: List[str],
            helper_socket_path: Path = Path('/run/bubblehelp/helper.socket'),
            no_child_timeout: Optional[int] = 3,
            reaper_pool_timer: int = 5,
            use_fixups: bool = True,
    ):
        self.startup_args = startup_args
        self.helper_socket_path = helper_socket_path

        # Server
        self.server: Optional[AbstractServer] = None

        # Event terminated
        self.terminated = Event()

        # Terminator variables
        self.terminator_look_for_command: Optional[str] = None
        try:
            # Startup command can be either by path or just command
            # IE: sh vs /bin/sh
            # We want to extract the final word as in /proc/{PID}/stat
            # the executable name is always reported as binary name
            # What if there are two different binaries with same name but
            # different paths????
            startup_command_or_path = startup_args[0].split('/')[-1]
            self.terminator_look_for_command = startup_command_or_path
        except IndexError:
            ...
        self.terminator_pool_timer = reaper_pool_timer
        self.termninator_watcher_task: Optional[Task[None]] = None

        # Fix-ups
        if not use_fixups:
            return

        # Make sure that XDG_RUNTIME_DIR is 700
        # otherwise KDE applicaitons do not work
        Path(get_runtime_dir()).chmod(0o700)

    @classmethod
    def iter_proc_process_directories(cls) -> Generator[Path, None, None]:
        proc_path = Path('/proc')
        # Iterate over items in /proc
        for proc_item in proc_path.iterdir():
            # If we found something without number as name
            # skip it as its not a process
            if proc_item.name.isnumeric():
                yield proc_item

    @classmethod
    def proc_has_process_command(cls, process_command: str) -> bool:
        for process_dir in cls.iter_proc_process_directories():
            # read cmdline file containing cmd arguments
            with open(process_dir / 'stat') as stat_file:
                # Read file and split by white space
                # The command argument is a second white space
                # separated argument so we only need to split 2 times
                stat_file_data_list = stat_file.read().split(maxsplit=2)
                # compare command
                # The command is enclosed in () round parenthesis
                # [1:-1] will remove them
                if process_command == stat_file_data_list[1][1:-1]:
                    return True

        return False

    @classmethod
    def process_has_child(cls, process_id: str = '1') -> bool:
        for process_dir in cls.iter_proc_process_directories():
            # PID 1 always has a parent
            if process_dir.name == '1':
                continue

            # Open /proc/PID/stat
            with open(process_dir / 'stat') as stat_file:
                # Read file and split by white space
                stat_file_data_list = stat_file.read().split()
                # 4th item is the parent pid
                if stat_file_data_list[3] == process_id:
                    return True

        return False

    async def termninator_watcher(self) -> None:
        if __debug__:
            print(
                'self.terminator_look_for_command: ',
                repr(self.terminator_look_for_command))

        while True:
            try:
                await sleep(self.terminator_pool_timer)  # wait timer

                if self.terminator_look_for_command is None:
                    is_time_to_termniate = not self.process_has_child()
                else:
                    is_time_to_termniate = not self.proc_has_process_command(
                        self.terminator_look_for_command
                    )

                if is_time_to_termniate:
                    if __debug__:
                        print('No children found. Terminating.')
                    create_task(self.stop_async())
                    return
            except CancelledError:
                return

    async def run_command(
        self,
        args_to_run: List[str],
        std_in_out_mode: Optional[int] = None,
    ) -> Optional[str]:

        if std_in_out_mode == DEVNULL:
            p = await create_subprocess_exec(
                *args_to_run,
                stdout=DEVNULL,
                stderr=DEVNULL,
                stdin=DEVNULL,
            )
        elif std_in_out_mode == PIPE:
            p = await create_subprocess_exec(
                *args_to_run,
                stdout=PIPE,
                stderr=STDOUT,
                stdin=PIPE,
            )
        else:
            p = await create_subprocess_exec(
                *args_to_run,
            )

        if std_in_out_mode is None:
            await p.wait()
        elif std_in_out_mode == PIPE:
            (stdout_data, _) = await p.communicate()
            return str(stdout_data)

        return None

    async def client_handler(
            self,
            reader: StreamReader,
            writter: StreamWriter) -> None:

        if __debug__:
            print('Client connected', flush=True)

        while True:
            line = await reader.readline()
            if not line:
                if __debug__:
                    print('Reached end of reader. Returnning', flush=True)
                writter.close()
                await writter.wait_closed()
                return

            request = request_selector(line)

            if isinstance(request, RequestPing):
                response = request.response_ping()
            elif isinstance(request, RequestRun):
                run_stdout = await self.run_command(
                    args_to_run=request.args_to_run,
                )
                if run_stdout is None:
                    continue
                else:
                    response = request.response_run(
                        text=run_stdout,
                    )

            writter.write(response)
            await writter.drain()

    async def start_async(self) -> None:
        self.server = await start_unix_server(
            self.client_handler,
            path=self.helper_socket_path,
        )
        if __debug__:
            print('Started unix server', flush=True)
        self.termninator_watcher_task = create_task(self.termninator_watcher())
        if self.startup_args:
            await self.run_command(self.startup_args)

    async def stop_async(self) -> None:

        if (self.termninator_watcher_task is not None
            and
                not self.termninator_watcher_task.done()):
            self.termninator_watcher_task.cancel()
            await self.termninator_watcher_task

        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

        self.terminated.set()
        if __debug__:
            print('Terminated', flush=True)

    def __await__(self) -> Generator[Any, None, bool]:
        # Pylint does not recognize that we get a coroutine object
        # not the boolean
        # pylint: disable=E1101
        coroutine = self.terminated.wait()
        return coroutine.__await__()


def get_helper_argument_parser() -> ArgumentParser:
    parser = ArgumentParser()

    parser.add_argument(
        '--shell',
        action='store_true',
    )

    parser.add_argument(
        'args_to_run',
        nargs=ARG_REMAINDER,
    )

    return parser


def bubblejail_helper_main() -> None:
    parser = get_helper_argument_parser()

    parsed_args = parser.parse_args()

    async def run_helper() -> None:
        if not parsed_args.shell:
            startup_args = parsed_args.args_to_run
        else:
            startup_args = ['/bin/sh']

        helper = BubblejailHelper(
            startup_args=startup_args
        )
        await helper.start_async()
        await helper

    async_run(run_helper())


if __name__ == '__main__':
    bubblejail_helper_main()

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

from asyncio import (AbstractServer, CancelledError, Event, StreamReader,
                     StreamWriter, Task, create_subprocess_exec, create_task)
from asyncio import run as async_run
from asyncio import sleep, start_unix_server
from asyncio.subprocess import DEVNULL, PIPE, STDOUT
from json import dumps as json_dumps
from json import loads as json_loads
from os import P_NOWAIT, waitpid
from pathlib import Path
from sys import argv
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
            helper_socket_path: Path = Path('/run/bubblehelp/helper.socket'),
            no_child_timeout: Optional[int] = 3,
            reaper_pool_timer: int = 5,
            use_fixups: bool = True,
            exec_argv: bool = True,
    ):
        self.helper_socket_path = helper_socket_path

        # Server
        self.server: Optional[AbstractServer] = None

        # Event terminated
        self.terminated = Event()

        # Child reaper variables
        self.no_child_timeout = no_child_timeout
        self.no_child_countdown = no_child_timeout
        self.reaper_pool_timer = reaper_pool_timer
        self.child_reaper_task: Optional[Task[None]] = None

        self.exec_argv = exec_argv

        # Fix-ups
        if not use_fixups:
            return

        # Make sure that XDG_RUNTIME_DIR is 700
        # otherwise KDE applicaitons do not work
        Path(get_runtime_dir()).chmod(0o700)

    async def child_reaper(self) -> None:

        while True:
            try:
                await sleep(self.reaper_pool_timer)  # wait timer
            except CancelledError:
                return

            try:
                while True:
                    # This loop tries to reap as many children as possible
                    pid, _ = waitpid(0, P_NOWAIT)
                    # If we managed to call waitpid reset termination timer
                    self.no_child_countdown = self.no_child_timeout
                    if pid == 0:
                        break
            except ChildProcessError:
                # If no_child_countdown is set to None means we don't want
                # the helper to shutdown because there are no children
                if self.no_child_countdown is not None:
                    # When there are no children start
                    # the termnination countdown
                    self.no_child_countdown -= 1
                    print(
                        'No child present. Countdown: ',
                        self.no_child_countdown,
                        flush=True,
                    )
                    if not self.no_child_countdown:
                        create_task(self.stop_async())
                        return

    async def run_command(
            self,
            args_to_run: List[str],
            wait_completion: bool = False,) -> Optional[str]:

        if wait_completion:
            p = await create_subprocess_exec(
                *args_to_run,
                stdout=PIPE,
                stderr=STDOUT,
                stdin=PIPE,
            )
            (stdout_data, _) = await p.communicate()
            return str(stdout_data)
        else:
            create_task(
                create_subprocess_exec(
                    *args_to_run,
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                    stdin=DEVNULL,
                )
            )
            return None

    async def client_handler(
            self,
            reader: StreamReader,
            writter: StreamWriter) -> None:
        print('Client connected', flush=True)
        while True:
            line = await reader.readline()
            if not line:
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
                    wait_completion=(True if request.request_id is not None
                                     else False),
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
        print('Started unix server', flush=True)
        self.child_reaper_task = create_task(self.child_reaper())
        if self.exec_argv:
            print(argv, flush=True)
            if len(argv) > 1:
                await self.run_command(argv[1:])

    async def stop_async(self) -> None:

        if (self.child_reaper_task is not None
            and
                not self.child_reaper_task.done()):
            self.child_reaper_task.cancel()
            await self.child_reaper_task

        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

        self.terminated.set()
        print('Terminated', flush=True)

    def __await__(self) -> Generator[Any, None, bool]:
        # Pylint does not recognize that we get a coroutine object
        # not the boolean
        # pylint: disable=E1101
        coroutine = self.terminated.wait()
        return coroutine.__await__()


if __name__ == '__main__':
    print('Main helper script starts', flush=True)

    async def run_helper() -> None:
        helper = BubblejailHelper()
        await helper.start_async()
        await helper

    async_run(run_helper())

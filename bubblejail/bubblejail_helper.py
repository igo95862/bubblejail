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

from asyncio import (Event, StreamReader, StreamWriter, create_task, sleep,
                     start_unix_server)
from json import dumps as json_dumps
from json import loads as json_loads
from os import P_NOWAIT, waitpid
from pathlib import Path
from typing import Any, Dict, Literal, Optional

RpcMethods = Literal['ping']


class JsonRpcBase:

    def __init__(self, request_id: Optional[str]):
        self.request_id = request_id

    @staticmethod
    def _encode_helper(dict_form: Dict[str, Any]) -> bytes:
        string_form = json_dumps(dict_form) + '\n'
        return string_form.encode()

    @staticmethod
    def _decode_helper(data: bytes) -> Dict[str, Any]:
        decoded_dict: Dict[str, Any] = json_loads(data)
        # Replace 'id' with 'request_id'
        decoded_dict['request_id'] = decoded_dict['id']
        decoded_dict.pop('id')

        return decoded_dict


class JsonRpcRequest(JsonRpcBase):
    def __init__(self, method: RpcMethods, request_id: Optional[str] = None):
        super().__init__(request_id)
        self.method = method

    def encode(self) -> bytes:
        dict_form = {
            "id": self.request_id,
            "method": self.method,
        }
        return self._encode_helper(dict_form)

    @classmethod
    def decode(cls, data: bytes) -> 'JsonRpcRequest':
        return JsonRpcRequest(**cls._decode_helper(data))


class JsonRpcResponce(JsonRpcBase):
    def __init__(self,
                 result: Dict[str, Any],
                 request_id: Optional[str] = None):
        super().__init__(request_id)
        self.result = result

    def encode(self) -> bytes:
        dict_form = {
            "id": self.request_id,
            "result": self.result,
        }
        return self._encode_helper(dict_form)

    @classmethod
    def decode(cls, data: bytes) -> 'JsonRpcResponce':
        return JsonRpcResponce(**cls._decode_helper(data))


class BubblejailHelper:
    def __init__(
        self,
            helper_socket_path: Path = Path('/tmp/bubble_sock'),
            no_child_timeout: int = 3,
            reaper_pool_timer: int = 5,
    ):
        self.helper_socket_path = helper_socket_path
        # Event needs to initialized in async function
        self.termination: Optional[Event] = None

        # Child reaper variables
        self.no_child_timeout = no_child_timeout
        self.no_child_countdown = no_child_timeout
        self.reaper_pool_timer = reaper_pool_timer

    async def child_reaper(self) -> None:
        if self.termination is None:
            raise ValueError('Termnination event not initialized')

        while True:
            await sleep(self.reaper_pool_timer)  # wait timer
            try:
                while True:
                    # This loop tries to reap as many children as possible
                    pid, _ = waitpid(0, P_NOWAIT)
                    # If we managed to call waitpid reset termination timer
                    self.no_child_countdown = self.no_child_timeout
                    if pid == 0:
                        break
            except ChildProcessError:
                # When there are no children start the termnination countdown
                self.no_child_countdown -= 1
                print(
                    'No child present. Countdown: ',
                    self.no_child_countdown,
                )
                if not self.no_child_countdown:
                    self.termination.set()
                    return

    async def client_handler(
            self,
            reader: StreamReader,
            writter: StreamWriter) -> None:
        print('Client connected')
        while True:
            line = await reader.readline()
            if not line:
                print('Reached end of reader. Returnning')
                writter.close()
                await writter.wait_closed()
                return

            request = JsonRpcRequest.decode(line)
            if request.method == 'ping':
                responce = JsonRpcResponce(
                    result={'pong': 'pong'},
                    request_id=request.request_id,
                )

                writter.write(responce.encode())
                await writter.drain()

    async def helper_main(self) -> None:
        server = await start_unix_server(
            self.client_handler,
            path=self.helper_socket_path,
        )
        print('Started unix server')
        self.termination = Event()
        create_task(self.child_reaper())
        await self.termination.wait()
        server.close()
        print('Terminated')

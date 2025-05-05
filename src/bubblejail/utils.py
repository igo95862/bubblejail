# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 igo95862
from __future__ import annotations

from asyncio import get_running_loop, wait_for
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Future
    from typing import BinaryIO


async def aread_once(read_io: BinaryIO, timeout: float = 3.0) -> bytes:
    loop = get_running_loop()
    read_future: Future[bytes] = loop.create_future()

    def read_callback() -> None:
        try:
            read_future.set_result(read_io.read())
        except BaseException as e:
            read_future.set_exception(e)

    try:
        loop.add_reader(read_io, read_callback)
        return await wait_for(read_future, timeout=timeout)
    finally:
        loop.remove_reader(read_io)

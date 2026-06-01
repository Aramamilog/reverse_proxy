from dataclasses import dataclass

import asyncio


@dataclass(frozen=True)
class Timeouts:
    connect: float
    read: float
    write: float
    total: float

    async def connect_timeout(self, coro):
        return await asyncio.wait_for(
            coro,
            timeout=self.connect,
        )

    async def read_timeout(self, coro):
        return await asyncio.wait_for(
            coro,
            timeout=self.read,
        )

    async def write_timeout(self, coro):
        return await asyncio.wait_for(
            coro,
            timeout=self.write,
        )

    async def total_timeout(self, coro):
        return await asyncio.wait_for(
            coro,
            timeout=self.total,
        )

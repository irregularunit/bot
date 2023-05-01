# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Optional

from aiohttp import ClientSession
from discord.utils import setup_logging
from redis.asyncio import Redis

from src.models.serenity import Serenity
from src.shared import SerenityConfig

if TYPE_CHECKING:
    from asyncpg import Pool, Record


def run_with_suppress(runner: Optional[asyncio.Runner]) -> None:
    with suppress(KeyboardInterrupt, asyncio.CancelledError):
        if runner is None:
            asyncio.run(main())
        else:
            runner.run(main())


async def setup() -> tuple[Serenity, Pool[Record], ClientSession]:
    setup_logging()
    config = SerenityConfig.parse_obj({})

    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    session: ClientSession = ClientSession()

    try:
        pool: Pool[Record] = await Serenity.create_pool(config.sql_dsn)

        if pool is None:
            raise RuntimeError("Failed to create database pool.")

        redis: Redis[Any] = Redis.from_url(config.redis_url)  # type: ignore

    except Exception as exc:
        raise exc

    serenity = Serenity(loop=loop, session=session, pool=pool, redis=redis)

    return serenity, pool, session


async def main() -> None:
    serenity, pool, session = await setup()

    async with serenity, pool, session:
        try:
            await serenity.start()
        except Exception as exc:
            raise exc


if __name__ == "__main__":
    if os.name in ("nt",):
        run_with_suppress(None)
    else:
        import uvloop

        if sys.version_info >= (3, 11):
            with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
                run_with_suppress(runner)
        else:
            uvloop.install()
            run_with_suppress(None)

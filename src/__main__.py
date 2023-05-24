# -*- coding: utf-8 -*-

"""
Serenity License (Attribution-NonCommercial-ShareAlike 4.0 International)

You are free to:

  - Share: copy and redistribute the material in any medium or format.
  - Adapt: remix, transform, and build upon the material.

The licensor cannot revoke these freedoms as long as you follow the license
terms.

Under the following terms:

  - Attribution: You must give appropriate credit, provide a link to the
    license, and indicate if changes were made. You may do so in any reasonable
    manner, but not in any way that suggests the licensor endorses you or your
    use.
  
  - Non-Commercial: You may not use the material for commercial purposes.
  
  - Share Alike: If you remix, transform, or build upon the material, you must
    distribute your contributions under the same license as the original.
  
  - No Additional Restrictions: You may not apply legal terms or technological
    measures that legally restrict others from doing anything the license
    permits.

This is a human-readable summary of the Legal Code. The full license is available
at https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Optional

from aiohttp import ClientSession
from discord import VoiceClient
from discord.utils import setup_logging
from redis.asyncio import Redis

from src.models.serenity import Serenity
from src.shared import SerenityConfig

if TYPE_CHECKING:
    from asyncpg import Pool, Record


VoiceClient.warn_nacl = False


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
            await serenity.close()
            raise exc


if __name__ == "__main__":
    if os.name in {"nt"}:
        run_with_suppress(None)
    else:
        import uvloop  # type: ignore

        if sys.version_info >= (3, 11):
            with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:  # type: ignore
                run_with_suppress(runner)
        else:
            uvloop.install()
            run_with_suppress(None)

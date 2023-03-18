from __future__ import annotations

import os
from asyncio import AbstractEventLoop, CancelledError, get_event_loop, run
from logging import Logger, getLogger
from typing import TYPE_CHECKING

from aiohttp import ClientSession

from bot import Bot
from bridges import RedisBridge
from settings import Config
from utils import setup_logging, suppress

if TYPE_CHECKING:
    from asyncpg import Pool, Record


log: Logger = getLogger(__name__)

os.environ["JISHAKU_NO_UNDERSCORE"] = "true"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "true"
os.environ["JISHAKU_HIDE"] = "false"
os.environ["JISHAKU_RETAIN"] = "true"


async def setup() -> tuple[Bot, Pool[Record], ClientSession]:
    setup_logging("INFO")
    prep_conf: Config = Config()  # type: ignore (my IDE doesn't get it)

    loop: AbstractEventLoop = get_event_loop()
    session: ClientSession = ClientSession()

    try:
        pool: Pool[Record] = await Bot.create_pool(dsn=prep_conf.psql)  # type: ignore
        redis: RedisBridge = RedisBridge.setup_redis(uri=prep_conf.redis)

        log.info("PostgreSQL and Redis successfully connected.")
    except Exception as exc:
        raise exc

    try:
        bot: Bot = Bot(loop=loop, session=session, pool=pool, redis=redis)
        log.info("Successfully created a bot instance.")
    except Exception as exc:
        raise exc

    return bot, pool, session


async def main() -> None:
    bot, pool, session = await setup()

    async with bot, pool, session:
        try:
            await bot.start()
        except Exception as exc:
            raise exc


if __name__ == "__main__":
    with suppress(KeyboardInterrupt, CancelledError, capture=False):
        run(main())
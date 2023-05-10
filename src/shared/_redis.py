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

import datetime as dt
from typing import TYPE_CHECKING, Any, AsyncGenerator, Optional, Union

import redis.asyncio as redis
from discord import utils

if TYPE_CHECKING:
    from src.models.serenity import Serenity

__all__: tuple[str, ...] = ("Publisher", "Subscriber")


class Publisher:
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity
        self.redis: redis.Redis[Any] = serenity.redis
        self.pubsub: Any = serenity.redis.pubsub()  # type: ignore

    async def publish(self, channel: str, message: Any) -> None:
        await self.redis.publish(channel, message)

    async def publish_after(
        self, channel: str, message: Any, delay: Union[int, float]
    ) -> None:
        await utils.sleep_until(when=utils.utcnow() + dt.timedelta(seconds=delay))

        async with self.redis.pubsub() as ps:  # type: ignore
            await ps.subscribe(channel)  # type: ignore
            await self.redis.publish(channel, message)


class Subscriber:
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity
        self.redis = serenity.redis
        self.pubsub = serenity.redis.pubsub()  # type: ignore

    async def listener(self, channel: str) -> AsyncGenerator[Optional[str], None]:
        await self.pubsub.subscribe(channel)  # type: ignore

        while True:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    yield message["data"].decode("utf-8")

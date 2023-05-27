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

from functools import singledispatchmethod
from typing import TYPE_CHECKING, Any, ClassVar, Dict, NamedTuple

from discord.ext import tasks

from src.shared import SerenityQueue

from .utils import get_insert_day, get_insert_month, get_insert_year  # type: ignore

if TYPE_CHECKING:
    from asyncpg import Pool, Record


__all__: tuple[str, ...] = ("SerenityCountingManager",)


class CountingEntry(NamedTuple):
    usnowflake: int
    gsnowflake: int
    message_timestamp: int
    message_type: CountingMessageType


class CountingMessageType:
    TypeMapping: ClassVar[Dict[str, int]] = {"COUNT": 1, "HUNT": 2, "BATTLE": 3}

    value: int
    name: str

    def __init__(self, value: int) -> None:
        self.value = value
        self.name = self._get_value_name()

    def _get_value_name(self) -> str:
        for name, value in self.TypeMapping.items():
            if value == self.value:
                return name

        raise ValueError(f"Invalid value `{self.value}` for CountingMessageType")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<CountingMessageType value={self.value} value_name={self.name}>"

    def linked_table(self) -> str:
        return f"serenity_user_{self.name.lower()}_messages"


class SerenityCountingManager:
    __slots__ = (
        "pool",
        "_batch_queue",
    )

    pool: Pool[Record]
    _batch_queue: SerenityQueue[CountingEntry]

    def __init__(self, pool: Pool[Record]) -> None:
        self.pool = pool
        self._batch_queue = SerenityQueue()

    @tasks.loop(seconds=10)
    async def _batch_insert(self) -> None:
        transformable = await self._batch_queue.get_many(1000)

        if not transformable:
            return

        insert_statement = """
            INSERT INTO serenity_user_daily_message_counter
                (usnowflake, gsnowflake, message_type, message_count, message_timestamp)
            VALUES
                ($1, $2, $3, $4, $5)
            ON CONFLICT (usnowflake, gsnowflake, message_type, message_timestamp)
            DO UPDATE SET
                message_count = serenity_user_daily_message_counter.message_count + $4
        """

        to_insert = [
            (entry.usnowflake, entry.gsnowflake, entry.message_type.name, 1, entry.message_timestamp)
            for entry in transformable
        ]

        async with self.pool.acquire() as connection:
            await connection.executemany(insert_statement, to_insert)

    async def _push_to_batch_queue(self, usnowflake: int, gsnowflake: int, message_type: CountingMessageType) -> None:
        message_timestamp = int(get_insert_day().timestamp())

        item = CountingEntry(
            usnowflake=usnowflake,
            gsnowflake=gsnowflake,
            message_type=message_type,
            message_timestamp=message_timestamp,
        )

        await self._batch_queue.put(item)

    @singledispatchmethod
    async def insert(
        self,
        message_type: Any,
        usnowflake: int,
        gsnowflake: int,
    ) -> None:
        raise TypeError(f"Invalid type `{type(message_type)}` for `message_type`")

    @insert.register
    async def _(self, message_type: int, usnowflake: int, gsnowflake: int) -> None:
        new_message_type = CountingMessageType(message_type)

        await self._push_to_batch_queue(usnowflake, gsnowflake, new_message_type)

    @insert.register
    async def _(self, message_type: str, usnowflake: int, gsnowflake: int) -> None:
        try:
            new_message = CountingMessageType.TypeMapping[message_type]
        except KeyError as exc:
            raise ValueError(f"Invalid value `{message_type}` for `message_type`") from exc

        new_message_type = CountingMessageType(new_message)

        await self._push_to_batch_queue(usnowflake, gsnowflake, new_message_type)

    @insert.register
    async def _(self, message_type: CountingMessageType, usnowflake: int, gsnowflake: int) -> None:
        await self._push_to_batch_queue(usnowflake, gsnowflake, message_type)

    async def _transform_daily_counts(self) -> None:
        ...

    async def _transform_monthly_counts(self) -> None:
        ...

    async def _transform_yearly_counts(self) -> None:
        ...

    async def start(self) -> None:
        tasks = (self._batch_insert,)

        for task in tasks:
            task.start()

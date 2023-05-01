# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from typing import TYPE_CHECKING, Self, Type

if TYPE_CHECKING:
    from datetime import datetime

    from asyncpg import Pool, Record


__all__: tuple[str, ...] = ("SerenityGuild", "SERENITY_GUILDS_LINKED_TABLE")


_logger = getLogger(__name__)

_LINKED_TABLES = (
    "serenity_guild_emotes",
    "serenity_guild_prefixes",
    "serenity_guild_snipes",
)
SERENITY_GUILDS_LINKED_TABLE = "serenity_guilds"


@dataclass
class SerenityGuild:
    id: int
    prefixes: list[str]
    counting_prefix: str
    created_at: datetime
    banned: bool = False

    @classmethod
    def from_record(cls: Type[Self], record: Record) -> Self:
        return cls(
            id=record["snowflake"],
            prefixes=record["prefixes"],
            banned=record["banned"],
            created_at=record["created_at"],
            counting_prefix=record["counting_prefix"],
        )

    @classmethod
    def from_default(cls: Type[Self], record: Record, prefixes: list[str]) -> Self:
        return cls(
            id=record["snowflake"],
            prefixes=prefixes,
            banned=record["banned"],
            created_at=record["created_at"],
            counting_prefix=record["counting_prefix"],
        )

    async def delete(self, pool: Pool[Record]) -> None:
        async with pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM serenity_guilds WHERE id = $1 CASCADE",
                self.id,
            )

        _logger.getChild("delete").info("Deleted guild %s from database", self.id)

    @property
    def link_tables(self) -> tuple[str, ...]:
        return _LINKED_TABLES

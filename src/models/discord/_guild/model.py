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


@dataclass(slots=True)
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

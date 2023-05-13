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
from time import time
from typing import TYPE_CHECKING, Any, Self, Type

from src.shared import ExceptionFactory, ExecptionLevel

if TYPE_CHECKING:
    from datetime import datetime

    from asyncpg import Pool, Record


__all__: tuple[str, ...] = (
    "SerenityUser",
    "SERENITY_USERS_LINKED_TABLE",
    "CountingSettings",
)


_logger = getLogger(__name__)

_LINKED_TABLES = (
    "serenity_user_settings",
    "serenity_user_avatars",
    "serenity_user_history",
    "serenity_user_presence",
)
SERENITY_USERS_LINKED_TABLE = "serenity_users"


@dataclass(slots=True)
class SerenityUser:
    id: int
    created_at: datetime
    locale: str
    timezone: str
    emoji_server_id: int
    counting: CountingSettings
    banned: bool = False

    @classmethod
    def from_record(cls: Type[Self], record: Record) -> Self:
        return cls(
            id=record["snowflake"],
            created_at=record["created_at"],
            locale=record["locale"],
            banned=record["banned"],
            timezone=record["timezone"],
            emoji_server_id=record["emoji_server_snowflake"],
            counting=CountingSettings(
                counter_message=record["counter_message"],
                hunt_battle_message=record["hunt_battle_message"],
            ),
        )

    @classmethod
    def from_default(cls: Type[Self], record: Record, settings: CountingSettings) -> Self:
        return cls(
            id=record["snowflake"],
            created_at=record["created_at"],
            locale=record["locale"],
            banned=record["banned"],
            timezone=record["timezone"],
            emoji_server_id=record["emoji_server_snowflake"],
            counting=settings,
        )

    @property
    def link_tables(self) -> tuple[str, ...]:
        return _LINKED_TABLES

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"

    async def delete(self, pool: Pool[Record]) -> None:
        async with pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM serenity_users WHERE id = $1 CASCADE",
                self.id,
            )

        _logger.getChild("delete").debug("Deleted %s", self.id)

    async def update(self, field: str, value: Any) -> SerenityUser:
        attr = getattr(self, field, None)

        if attr is None:
            raise ExceptionFactory.create_exception(
                ExecptionLevel.ERROR,
                f"Error while updating {self.id}'s {field} with {value}",
            )

        setattr(self, field, value)
        _logger.getChild("update").debug("Updated %s's %s to %s", self.id, field, value)

        return self


@dataclass
class CountingSettings:
    counter_message: str
    hunt_battle_message: str

    last_battle: float = time()
    last_hunt: float = time()
    last_count: float = time()

    def can_battle(self, now: int) -> bool:
        return now - self.last_battle > 15

    def can_hunt(self, now: int) -> bool:
        return now - self.last_hunt > 15

    def can_count(self, now: int) -> bool:
        return now - self.last_count > 10

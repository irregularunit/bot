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

from typing import TYPE_CHECKING, Optional

from src.shared import ExceptionFactory

from .model import CountingSettings, SerenityUser

if TYPE_CHECKING:
    from asyncpg import Pool, Record

__all__: tuple[str, ...] = ("SerenityUserManager",)


class SerenityUserManager:
    def __init__(self, pool: Pool[Record]) -> None:
        self.pool = pool

    async def get_user(self, snowflake: int, /) -> Optional[SerenityUser]:
        query = """
            SELECT
                u.*, s.counter_message, s.hunt_battle_message
            FROM
                serenity_users AS u
            LEFT JOIN serenity_user_settings AS s ON u.snowflake = s.snowflake
            WHERE
                u.snowflake = $1
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                record = await conn.fetchrow(query, snowflake)

        return None if record is None else SerenityUser.from_record(record)

    async def create_user(self, snowflake: int, /) -> SerenityUser:
        query = """
            INSERT INTO serenity_users 
                (snowflake)
            VALUES 
                ($1)
            RETURNING *
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                record = await conn.fetchrow(query, snowflake)

        if record is None:
            raise ExceptionFactory.create_error_exception("Failed to create user")

        settings = CountingSettings(
            counter_message="Your cooldown is up!",
            hunt_battle_message="You hunt/battle cooldown is up!",
        )

        return SerenityUser.from_default(record, settings)

    async def update_user(self, user: SerenityUser, /) -> None:
        query = """
            UPDATE serenity_users
            SET
                locale = $1,
                timezone = $2,
                emoji_server_id = $3,
                banned = $4,
                pronouns = $5
            WHERE
                snowflake = $6
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    query,
                    user.locale,
                    user.timezone,
                    user.emoji_server_snowflake,
                    user.banned,
                    user.pronouns,
                    user.id,
                )

    async def get_or_create_user(self, snowflake: int, /) -> SerenityUser:
        user = await self.get_user(snowflake)

        if user is None:
            user = await self.create_user(snowflake)

        return user

    async def delete_user(self, snowflake: int, /) -> None:
        query = """
            DELETE FROM serenity_users
            WHERE
                snowflake = $1
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, snowflake)

    async def gather_users(self) -> list[SerenityUser]:
        query = """
            SELECT
                u.*, s.counter_message, s.hunt_battle_message
            FROM
                serenity_users AS u
            LEFT JOIN serenity_user_settings AS s ON u.snowflake = s.snowflake
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                records = await conn.fetch(query)

        return [SerenityUser.from_record(record) for record in records]

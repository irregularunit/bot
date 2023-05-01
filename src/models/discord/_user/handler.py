# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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

        if record is None:
            return None

        return SerenityUser.from_record(record)

    async def create_user(self, snowflake: int, /) -> SerenityUser:
        query = """
            INSERT INTO serenity_users (snowflake)
            VALUES ($1)
            RETURNING *
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                record = await conn.fetchrow(query, snowflake)

        if record is None:
            raise Exception("Failed to create user")

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
                banned = $4
            WHERE
                snowflake = $5
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    query,
                    user.locale,
                    user.timezone,
                    user.emoji_server_id,
                    user.banned,
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

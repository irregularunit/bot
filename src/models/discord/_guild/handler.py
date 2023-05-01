# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .model import SerenityGuild

if TYPE_CHECKING:
    from asyncpg import Pool, Record


__all__: tuple[str, ...] = ("SerenityGuildManager",)


class SerenityGuildManager:
    def __init__(self, pool: Pool[Record]) -> None:
        self.pool = pool

    async def get_guild(self, snowflake: int, /) -> Optional[SerenityGuild]:
        query = """
            SELECT
                serenity_guilds.snowflake AS snowflake,
                array_agg(serenity_guild_prefixes.prefix) AS prefixes,
                serenity_guilds.banned AS banned,
                serenity_guilds.counting_prefix AS counting_prefix,
                serenity_guilds.created_at AS created_at
            FROM
                serenity_guilds
            LEFT JOIN serenity_guild_prefixes ON serenity_guilds.snowflake = serenity_guild_prefixes.snowflake
            WHERE
                serenity_guilds.snowflake = $1
            GROUP BY
                serenity_guilds.snowflake
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                record = await conn.fetchrow(query, snowflake)

        if record is None:
            return None

        return SerenityGuild.from_record(record)

    async def create_guild(self, snowflake: int, /) -> SerenityGuild:
        query = """
            INSERT INTO serenity_guilds (snowflake)
            VALUES ($1)
            RETURNING *
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                record = await conn.fetchrow(query, snowflake)

        if record is None:
            raise Exception("Failed to create guild")

        return SerenityGuild.from_default(record, ["s!", "s."])

    async def update_guild(self, guild: SerenityGuild, /) -> None:
        query = """
            UPDATE serenity_guilds
            SET
                banned = $1,
                counting_prefix = $2
            WHERE
                snowflake = $3
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, guild.banned, guild.counting_prefix, guild.id)

    async def get_or_create_guild(self, snowflake: int, /) -> SerenityGuild:
        guild = await self.get_guild(snowflake)

        if guild is None:
            guild = await self.create_guild(snowflake)

        return guild

    async def delete_guild(self, snowflake: int, /) -> None:
        query = """
            DELETE FROM serenity_guilds
            WHERE
                snowflake = $1
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, snowflake)

    async def gather_guilds(self) -> list[SerenityGuild]:
        query = """
            SELECT
                serenity_guilds.snowflake AS snowflake,
                array_agg(serenity_guild_prefixes.prefix) AS prefixes,
                serenity_guilds.banned AS banned,
                serenity_guilds.counting_prefix AS counting_prefix,
                serenity_guilds.created_at AS created_at
            FROM
                serenity_guilds
            LEFT JOIN serenity_guild_prefixes ON serenity_guilds.snowflake = serenity_guild_prefixes.snowflake
            GROUP BY
                serenity_guilds.snowflake
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                records = await conn.fetch(query)

        return [SerenityGuild.from_record(record) for record in records]

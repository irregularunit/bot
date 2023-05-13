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
            INSERT INTO serenity_guilds 
                (snowflake)
            VALUES 
                ($1)
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

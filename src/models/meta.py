"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import io
from logging import Logger, getLogger
from typing import TYPE_CHECKING, Optional, Type

from asyncpg import Pool, Record

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory

if TYPE_CHECKING:
    from datetime import datetime

__all__: tuple[str, ...] = ("User", "Guild", "ModelManager")

log: Logger = getLogger(__name__)


class Model:
    __slots__: tuple[str, ...] = ("id", "created_at")

    def __init__(self, *, id: int, created_at: datetime) -> None:
        self.id: int = id
        self.created_at: datetime = created_at

    @classmethod
    def from_record(cls: Type[Model], record: Record) -> ...:
        raise NotImplementedError

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"


class User(Model):
    __slots__: tuple[str, ...] = ("emoji_server", "timezone", "id", "created_at")

    def __init__(self, *, id: int, created_at: datetime, emoji_server: int, timezone: str) -> None:
        super().__init__(id=id, created_at=created_at)
        self.emoji_server: int = emoji_server
        self.timezone: str = timezone

    @classmethod
    def from_record(cls: Type[User], record: Record) -> User:
        return cls(
            id=record["uuid"],
            emoji_server=record["emoji_server"],
            timezone=record["timezone"],
            created_at=record["created_at"],
        )

    async def delete(self, pool: Pool) -> None:
        to_cascade = [
            "avatar_history",
            "item_history",
            "presence_history",
            "users",
            "owo_counting",
        ]
        query = io.StringIO()

        for table in to_cascade:
            query.write(f"DELETE FROM {table} WHERE uuid = $1;")

        async with pool.acquire() as connection:
            await connection.execute(query.getvalue(), self.id)


class Guild(Model):
    __slots__: tuple[str, ...] = ("prefixes", "owo_prefix", "owo_counting", "id", "created_at")

    def __init__(
        self, *, id: int, created_at: datetime, prefixes: list[str], owo_prefix: str, owo_counting: bool
    ) -> None:
        super().__init__(id=id, created_at=created_at)
        self.prefixes: list[str] = prefixes
        self.owo_prefix: str = owo_prefix
        self.owo_counting: bool = owo_counting

    @classmethod
    def from_record(cls: Type[Guild], record: Record) -> Guild:
        return cls(
            id=record["gid"],
            prefixes=record["prefixes"],
            owo_prefix=record["owo_prefix"],
            owo_counting=record["owo_counting"],
            created_at=record["created_at"],
        )


class ModelManager:
    def __init__(self, pool: Pool) -> None:
        self.pool = pool

    async def create_user(self, user_id: int) -> User:
        query: str = """
        INSERT INTO users (uuid)
        VALUES ($1)
        ON CONFLICT (uuid) DO NOTHING
        RETURNING *
        """
        async with self.pool.acquire() as connection:
            record: Record | None = await connection.fetchrow(query, user_id)

        if not record:
            maybe_user: User | None = await self.get_user(user_id)
            if not maybe_user:
                raise UserFeedbackExceptionFactory.create("Failed to create user", ExceptionLevel.ERROR)
            return maybe_user

        return User.from_record(record)

    async def get_user(self, user_id: int) -> Optional[User]:
        query: str = "SELECT * FROM users WHERE uuid = $1"

        async with self.pool.acquire() as connection:
            record: Record | None = await connection.fetchrow(query, user_id)

        if record is None:
            log.getChild("get_user").debug("Failed to get user with id %s", user_id)
            return None
        return User.from_record(record)

    async def get_or_create_user(self, user_id: int) -> User:
        user: User | None = await self.get_user(user_id)
        if user is None:
            user = await self.create_user(user_id)
        return user

    async def set_user_timezone(self, user_id: int, timezone: str) -> None:
        query: str = "UPDATE users SET timezone = $1 WHERE uuid = $2"
        await self.pool.execute(query, timezone, user_id)

    async def get_all_users(self) -> dict[int, User]:
        query: str = "SELECT * FROM users"

        async with self.pool.acquire() as connection:
            records: list[Record] = await connection.fetch(query)

        users: dict[int, User] = {record["uuid"]: User.from_record(record) for record in records}
        return users

    async def create_guild(self, guild_id: int) -> Guild:
        query: str = """
        INSERT INTO guilds (gid)
        VALUES ($1)
        ON CONFLICT (gid) DO NOTHING
        RETURNING *
        """

        async with self.pool.acquire() as connection:
            record: Record | None = await connection.fetchrow(query, guild_id)

        if not record:
            maybe_guild: Guild | None = await self.get_guild(guild_id)
            if not maybe_guild:
                raise UserFeedbackExceptionFactory.create("Failed to create guild", ExceptionLevel.ERROR)
            return maybe_guild

        instance: Guild = Guild(
            id=record["gid"],
            prefixes=["pls", "pls "],
            owo_prefix=record["owo_prefix"],
            owo_counting=record["owo_counting"],
            created_at=record["created_at"],
        )
        return instance

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        query: str = """
        SELECT guilds.gid as gid,
            array_agg(guild_prefixes.prefix) as prefixes,
            guilds.owo_prefix as owo_prefix,
            guilds.owo_counting as owo_counting,
            guilds.created_at as created_at
        FROM guilds LEFT JOIN guild_prefixes ON guilds.gid = guild_prefixes.gid
        WHERE guilds.gid = $1
        GROUP BY guilds.gid    
        """

        async with self.pool.acquire() as connection:
            record: Record | None = await connection.fetchrow(query, guild_id)

        if record is None:
            _log: Logger = log.getChild("get_guild")
            _log.debug("Failed to get guild with id %s", guild_id)
            return None
        return Guild.from_record(record)

    async def get_or_create_guild(self, guild_id: int) -> Guild:
        guild: Guild | None = await self.get_guild(guild_id)
        if guild is None:
            guild = await self.create_guild(guild_id)
        return guild

    async def get_all_guilds(self) -> dict[int, Guild]:
        query: str = """
        SELECT guilds.gid as gid,
            array_agg(guild_prefixes.prefix) as prefixes,
            guilds.owo_prefix as owo_prefix,
            guilds.owo_counting as owo_counting,
            guilds.created_at as created_at
        FROM guilds LEFT JOIN guild_prefixes ON guilds.gid = guild_prefixes.gid
        GROUP BY guilds.gid
        """

        async with self.pool.acquire() as connection:
            records: list[Record] = await connection.fetch(query)

        guilds: dict[int, Guild] = {record["gid"]: Guild.from_record(record) for record in records}
        return guilds

    async def remove_guild_prefix(self, guild: Guild, prefix: str) -> Optional[Guild]:
        if prefix not in guild.prefixes:
            raise UserFeedbackExceptionFactory.create("That prefix does not exist", ExceptionLevel.WARNING)

        query: str = "DELETE FROM guild_prefixes WHERE gid = $1 AND prefix = $2"

        async with self.pool.acquire() as connection:
            await connection.execute(query, guild.id, prefix)

        guild.prefixes.remove(prefix)
        return guild

    async def add_guild_prefix(self, guild: Guild, prefix: str) -> Optional[Guild]:
        if prefix in guild.prefixes:
            raise UserFeedbackExceptionFactory.create("That prefix already exists", ExceptionLevel.WARNING)

        query: str = "INSERT INTO guild_prefixes (gid, prefix) VALUES ($1, $2)"

        async with self.pool.acquire() as connection:
            await connection.execute(query, guild.id, prefix)

        guild.prefixes.append(prefix)
        return guild

    async def set_guild_owo_prefix(self, guild: Guild, prefix: str) -> Guild:
        query: str = "UPDATE guilds SET owo_prefix = $1 WHERE gid = $2"

        async with self.pool.acquire() as connection:
            await connection.execute(query, prefix, guild.id)

        guild.owo_prefix = prefix
        return guild

    async def toggle_guild_owo_counting(self, guild: Guild) -> Optional[Guild]:
        query: str = "UPDATE guilds SET owo_counting = NOT owo_counting WHERE gid = $1"

        async with self.pool.acquire() as connection:
            await connection.execute(query, guild.id)

        guild.owo_counting = not guild.owo_counting
        return guild

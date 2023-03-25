"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger, getLogger
from typing import TYPE_CHECKING, Optional, Type

from asyncpg import Pool, Record

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory

if TYPE_CHECKING:
    from datetime import datetime

__all__: tuple[str, ...] = ("User", "Guild", "ModelManager")

log: Logger = getLogger(__name__)


@dataclass
class Model:
    id: int
    created_at: datetime

    @classmethod
    def from_record(cls: Type[Model], record: Record) -> ...:
        raise NotImplementedError

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"


@dataclass
class User(Model):
    timezone: str

    @classmethod
    def from_record(cls: Type[User], record: Record) -> User:
        return cls(
            id=record["uid"],
            timezone=record["timezone"],
            created_at=record["created_at"],
        )


@dataclass
class Guild(Model):
    prefixes: list[str]
    owo_prefix: str
    owo_counting: bool

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
        INSERT INTO users (uid)
        VALUES ($1)
        ON CONFLICT (uid) DO NOTHING
        RETURNING *
        """
        record: Record | None = await self.pool.fetchrow(query, user_id)

        if not record:
            maybe_user: User | None = await self.get_user(user_id)
            if not maybe_user:
                raise UserFeedbackExceptionFactory.create("Failed to create user", ExceptionLevel.ERROR)
            return maybe_user

        return User.from_record(record)

    async def get_user(self, user_id: int) -> Optional[User]:
        query: str = "SELECT * FROM users WHERE uid = $1"
        record: Record | None = await self.pool.fetchrow(query, user_id)
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
        query: str = "UPDATE users SET timezone = $1 WHERE uid = $2"
        await self.pool.execute(query, timezone, user_id)

    async def get_all_users(self) -> dict[int, User]:
        query: str = "SELECT * FROM users"
        records: list[Record] = await self.pool.fetch(query)
        users: dict[int, User] = {record["uid"]: User.from_record(record) for record in records}
        return users

    async def create_guild(self, guild_id: int) -> Guild:
        query: str = """
        INSERT INTO guilds (gid)
        VALUES ($1)
        ON CONFLICT (gid) DO NOTHING
        RETURNING *
        """
        record: Record | None = await self.pool.fetchrow(query, guild_id)

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
        record: Record | None = await self.pool.fetchrow(query, guild_id)
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
        records: list[Record] = await self.pool.fetch(query)
        guilds: dict[int, Guild] = {record["gid"]: Guild.from_record(record) for record in records}
        return guilds

    async def remove_guild_prefix(self, guild: Guild, prefix: str) -> Optional[Guild]:
        if prefix not in guild.prefixes:
            raise UserFeedbackExceptionFactory.create("That prefix does not exist", ExceptionLevel.WARNING)
        query: str = "DELETE FROM guild_prefixes WHERE gid = $1 AND prefix = $2"
        await self.pool.execute(query, guild.id, prefix)

        guild.prefixes.remove(prefix)
        return guild

    async def add_guild_prefix(self, guild: Guild, prefix: str) -> Optional[Guild]:
        if prefix in guild.prefixes:
            raise UserFeedbackExceptionFactory.create("That prefix already exists", ExceptionLevel.WARNING)
        query: str = "INSERT INTO guild_prefixes (gid, prefix) VALUES ($1, $2)"
        await self.pool.execute(query, guild.id, prefix)

        guild.prefixes.append(prefix)
        return guild

    async def set_guild_owo_prefix(self, guild: Guild, prefix: str) -> Optional[Guild]:
        query: str = "UPDATE guilds SET owo_prefix = $1 WHERE gid = $2"
        await self.pool.execute(query, prefix, guild.id)

        guild.owo_prefix = prefix
        return guild

    async def toggle_guild_owo_counting(self, guild: Guild) -> Optional[Guild]:
        query: str = "UPDATE guilds SET owo_counting = NOT owo_counting WHERE gid = $1"
        await self.pool.execute(query, guild.id)

        guild.owo_counting = not guild.owo_counting
        return

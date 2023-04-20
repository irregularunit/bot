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
BOT_ID: int = 1054123882384212078


class Model:
    """Base model class for custom psql models.

    Attributes
    ----------
    `id`
        The id of the model.
    `created_at`
        The time the model was created.
    """

    __slots__: tuple[str, ...] = ("id", "created_at")

    def __init__(self, *, id: int, created_at: datetime) -> None:
        self.id: int = id
        self.created_at: datetime = created_at

    @classmethod
    def from_record(cls: Type[Model], record: Record) -> ...:
        """Meant to be overridden by subclasses.

        Parameters
        ----------
        record: `asyncpg.Record`
            The record to create the model from.

        Returns
        -------
        `Model`
            The model created from the record.
        """
        raise NotImplementedError

    @property
    def mention(self) -> str:
        """The mention of the model."""
        return f"<@{self.id}>"


class User(Model):
    """A custom user model.

    Attributes
    ----------
    `emoji_server`
        The id of the emoji server the user is in.
    `timezone`
        The timezone of the user.
    `id`
        The id of the user.
    `created_at`
        The time the user was created.
    """

    __slots__: tuple[str, ...] = (
        "emoji_server",
        "timezone",
    )

    def __init__(
        self,
        *,
        id: int,
        created_at: datetime,
        emoji_server: int,
        timezone: str,
    ) -> None:
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

    async def delete(self, pool: Pool[Record]) -> None:
        """Delete the user from the database.

        Parameters
        ----------
        pool: `asyncpg.Pool`
            The pool to delete the user from.
        """
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
    """A custom guild model.

    Attributes
    ----------
    `prefixes`
        The prefixes of the guild.
    `owo_prefix`
        The owo prefix of the guild.
    `owo_counting`
        Whether or not the guild is owo counting.
    `id`
        The id of the guild.
    `created_at`
        The time the guild was created.
    """

    __slots__: tuple[str, ...] = (
        "prefixes",
        "owo_prefix",
        "owo_counting",
    )

    def __init__(
        self,
        *,
        id: int,
        created_at: datetime,
        prefixes: list[str],
        owo_prefix: str,
        owo_counting: bool,
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
    """A model manager for all psql models.

    Attributes
    ----------
    `pool`
        The pool to use for the model manager.
    """

    def __init__(self, pool: Pool[Record]) -> None:
        self.pool = pool

    async def create_user(self, user_id: int) -> User:
        """Create a user in the database.

        Parameters
        ----------
        user_id: `int`
            The id of the user to create.

        Returns
        -------
        `User`
            The user created.

        Raises
        ------
        `UserFeedbackException`
            If the user could not be created.
        """

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
                raise UserFeedbackExceptionFactory.create(
                    "Failed to create user", ExceptionLevel.ERROR
                )
            return maybe_user

        return User.from_record(record)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user from the database.

        Parameters
        ----------
        user_id: `int`
            The id of the user to get.

        Returns
        -------
        `Optional[User]`
            The user if found, else `None`.
        """

        query: str = "SELECT * FROM users WHERE uuid = $1"

        async with self.pool.acquire() as connection:
            record: Record | None = await connection.fetchrow(query, user_id)

        if record is None:
            log.getChild("get_user").debug("Failed to get user with id %s", user_id)
            return None
        return User.from_record(record)

    async def get_or_create_user(self, user_id: int) -> User:
        """Get a user from the database, or create one if it doesn't exist.

        Parameters
        ----------
        user_id: `int`
            The id of the user to get or create.

        Returns
        -------
        `User`
            The user.
        """

        user: User | None = await self.get_user(user_id)
        if user is None:
            user = await self.create_user(user_id)
        return user

    async def set_user_timezone(self, user: User, timezone: str) -> User:
        """Set the timezone of a user.

        Parameters
        ----------
        user_id: `int`
            The id of the user to set the timezone of.
        timezone: `str`
            The timezone to set.
        """

        query: str = "UPDATE users SET timezone = $1 WHERE uuid = $2"

        async with self.pool.acquire() as connection:
            await connection.execute(query, timezone, user.id)

        user.timezone = timezone
        return user

    async def set_user_emoji_server(self, user: User, emoji_server: int) -> User:
        """Set the emoji server of a user.

        Parameters
        ----------
        user: `User`
            The user to set the emoji server of.
        emoji_server: `int`
            The emoji server to set.

        Returns
        -------
        `User`
            The user.
        """

        query: str = "UPDATE users SET emoji_server = $1 WHERE uuid = $2"

        async with self.pool.acquire() as connection:
            await connection.execute(query, emoji_server, user.id)

        user.emoji_server = emoji_server
        return user

    async def get_all_users(self) -> dict[int, User]:
        """Get all users from the database.

        Returns
        -------
        `dict[int, User]`
            A dictionary of all users.
        """

        query: str = "SELECT * FROM users"

        async with self.pool.acquire() as connection:
            records: list[Record] = await connection.fetch(query)

        users: dict[int, User] = {record["uuid"]: User.from_record(record) for record in records}
        return users

    async def create_guild(self, guild_id: int) -> Guild:
        """Create a guild in the database.

        Parameters
        ----------
        guild_id: `int`
            The id of the guild to create.

        Returns
        -------
        `Guild`
            The guild created.

        Raises
        ------
        `UserFeedbackException`
            If the guild could not be created.
        """

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
                raise UserFeedbackExceptionFactory.create(
                    "Failed to create guild", ExceptionLevel.ERROR
                )
            return maybe_guild

        instance: Guild = Guild(
            id=record["gid"],
            prefixes=["s.", "s!"],
            owo_prefix=record["owo_prefix"],
            owo_counting=record["owo_counting"],
            created_at=record["created_at"],
        )
        return instance

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """Get a guild from the database.

        Parameters
        ----------
        guild_id: `int`
            The id of the guild to get.

        Returns
        -------
        `Optional[Guild]`
            The guild if found, else `None`.
        """

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
        """Get a guild from the database, or create one if it doesn't exist.

        Parameters
        ----------
        guild_id: `int`
            The id of the guild to get or create.

        Returns
        -------
        `Guild`
            The guild.
        """

        guild: Guild | None = await self.get_guild(guild_id)
        if guild is None:
            guild = await self.create_guild(guild_id)
        return guild

    async def get_all_guilds(self) -> dict[int, Guild]:
        """Get all guilds from the database.

        Returns
        -------
        `dict[int, Guild]`
            A dictionary of all guilds.
        """

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

    async def remove_guild_prefix(self, guild: Guild, prefix: str) -> Guild:
        """Remove a prefix from a guild.

        Parameters
        ----------
        guild: `Guild`
            The guild to remove the prefix from.
        prefix: `str`
            The prefix to remove.

        Returns
        -------
        `Guild`
            The guild.

        Raises
        ------
        `UserFeedbackException`
            If the prefix does not exist.
        """

        if prefix not in guild.prefixes:
            raise UserFeedbackExceptionFactory.create(
                "That prefix does not exist", ExceptionLevel.WARNING
            )

        query: str = "DELETE FROM guild_prefixes WHERE gid = $1 AND prefix = $2"

        async with self.pool.acquire() as connection:
            await connection.execute(query, guild.id, prefix)

        guild.prefixes.remove(prefix)
        return guild

    async def add_guild_prefix(self, guild: Guild, prefix: str) -> Guild:
        """Add a prefix to a guild.

        Parameters
        ----------
        guild: `Guild`
            The guild to add the prefix to.
        prefix: `str`
            The prefix to add.

        Returns
        -------
        `Guild`
            The guild.

        Raises
        ------
        `UserFeedbackException`
            If the prefix already exists or is reserved.
        """

        if prefix in guild.prefixes or len(prefix) > 5:
            raise UserFeedbackExceptionFactory.create(
                "That prefix already exists", ExceptionLevel.WARNING
            )

        if prefix in [f"<@!{BOT_ID}>", f"<@{BOT_ID}>"]:
            raise UserFeedbackExceptionFactory.create(
                "That prefix is already used and reserved",
                ExceptionLevel.WARNING,
            )

        query: str = "INSERT INTO guild_prefixes (gid, prefix) VALUES ($1, $2)"

        async with self.pool.acquire() as connection:
            await connection.execute(query, guild.id, prefix)

        guild.prefixes.append(prefix)
        return guild

    async def set_guild_owo_prefix(self, guild: Guild, prefix: str) -> Guild:
        """Set the owo prefix for a guild.

        Parameters
        ----------
        guild: `Guild`
            The guild to set the owo prefix for.
        prefix: `str`
            The owo prefix to set.

        Returns
        -------
        `Guild`
            The guild.
        """

        query: str = "UPDATE guilds SET owo_prefix = $1 WHERE gid = $2"

        async with self.pool.acquire() as connection:
            await connection.execute(query, prefix, guild.id)

        guild.owo_prefix = prefix
        return guild

    async def toggle_guild_owo_counting(self, guild: Guild) -> Guild:
        """Toggle owo counting for a guild.

        Parameters
        ----------
        guild: `Guild`
            The guild to toggle owo counting for.

        Returns
        -------
        `Guild`
            The guild.
        """

        query: str = "UPDATE guilds SET owo_counting = NOT owo_counting WHERE gid = $1"

        async with self.pool.acquire() as connection:
            await connection.execute(query, guild.id)

        guild.owo_counting = not guild.owo_counting
        return guild

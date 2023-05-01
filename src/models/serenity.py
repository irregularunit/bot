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

import asyncio
import re
from functools import cached_property
from logging import Logger, getLogger
from typing import TYPE_CHECKING, Any, Coroutine, Self, Type, TypeVar

import discord
import orjson
from aiohttp import ClientError
from asyncpg import create_pool
from discord.ext import commands
from redis.asyncio import Redis
from typing_extensions import override

from src import __author__, __version__
from src.interfaces import GuildMessagable
from src.models.discord import (
    INTENTS,
    ExponentialBackoff,
    MobileGateway,
    SerenityContext,
    SerenityGuild,
    SerenityMixin,
    SerenityModelManager,
    SerenityUser,
)
from src.models.discord._bot.cache import SerenityUserCache
from src.shared import ExceptionFactory, ExecptionLevel, SerenityConfig

if TYPE_CHECKING:
    from datetime import datetime

    from aiohttp import ClientSession
    from asyncpg import Pool, Record


__all__: tuple[str, ...] = ("Serenity", "SerenityT")

_config = SerenityConfig.parse_obj({})
_logger = getLogger(__name__)

SerenityT = TypeVar("SerenityT", bound="Serenity", covariant=True)
SerenityContextT = TypeVar("SerenityContextT", bound="SerenityContext", covariant=True)


class Serenity(SerenityMixin, commands.Bot):  # type: ignore
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        pool: Pool[Record],
        session: ClientSession,
        redis: Redis[Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            command_prefix=self.get_prefix,
            intents=INTENTS,
            case_insensitive=True,
            owner_ids=_config.OWNER_IDS,
            **kwargs,
        )
        self.loop = loop
        self.config = _config
        self.session = session
        self.uptime: datetime

        self.user_cache = SerenityUserCache.from_none(500)
        self.model_manager = SerenityModelManager(pool)

        self.cached_guilds: dict[int, SerenityGuild] = {}
        self.cached_prefixes: dict[int, re.Pattern[str]] = {}

        self._pool = pool
        self._redis = redis

    @cached_property
    def version(self) -> str:
        return __version__

    @cached_property
    def author(self) -> str:
        return __author__

    @staticmethod
    @discord.utils.copy_doc(create_pool)
    async def create_pool(*args: Any, **kwargs: Any) -> Pool[Record]:
        init = kwargs.pop("init", None)

        def _encode_jsonb(obj: Any) -> str:
            return orjson.dumps(obj).decode('utf-8')

        def _decode_jsonb(data: str) -> Any:
            return orjson.loads(data)

        async def _init(conn: ...) -> None:
            await conn.set_type_codec(
                "jsonb",
                encoder=_encode_jsonb,
                decoder=_decode_jsonb,
                schema="pg_catalog",
            )
            if init is not None:
                await init(conn)

        pool: Pool[Record] | None = await create_pool(*args, init=_init, **kwargs)

        if pool is None:
            raise ExceptionFactory.create_exception(
                ExecptionLevel.ERROR, "Failed to create database pool."
            )

        return pool

    async def load_schema(self, schema: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(schema)

    @override
    async def get_context(
        self,
        message: discord.Message | discord.Interaction[Self],
        *,
        cls: Type[SerenityContext] = SerenityContext,
    ) -> SerenityContext:
        return await super().get_context(message, cls=cls or commands.Context[Self])

    async def gather_and_log(self, coros: list[Coroutine[Any, Any, Any]]) -> list[Any]:
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                _logger.error(
                    "Exception %s with error %s", result.__class__.__name__, result
                )
        return results

    @override
    async def setup_hook(self) -> None:
        # fmt: off
        await asyncio.gather(
            *[self.gather_and_log([self.load_extension(ext) for ext in (list(self.walk_plugins()) + ["jishaku"])])],
            *[self.gather_and_log([self.load_schema(schema.read_text()) for schema in self.walk_schemas()])],
        )
        # fmt: on

        users = await self.model_manager.gather_users()
        guilds = await self.model_manager.gather_guilds()

        self.user_cache.insert_many(*users)
        self.cached_guilds.update({guild.id: guild for guild in guilds})

    @override
    async def get_prefix(self, message: discord.Message, /) -> list[str] | str:
        if message.guild is None:
            # Our bot is not meant to be used in DMs.
            raise ExceptionFactory.create_exception(
                ExecptionLevel.ERROR, "Sorry, I don't do DMs."
            )

        if message.guild.id not in self.cached_prefixes:
            guild = await self.get_or_create_guild(message.guild.id)

            if guild.prefixes[0] is not None:
                pattern = self.compile_prefixes(guild.prefixes)
            else:
                if self.user is None:
                    raise RuntimeError("Bot is not ready.")

                pattern = re.compile(fr"<@!?{self.user.id}>", re.IGNORECASE)

            self.cached_prefixes[guild.id] = pattern

        if match := self.cached_prefixes[message.guild.id].match(message.content):
            return match.group(0)

        return commands.when_mentioned(self, message)

    async def get_or_create_guild(self, guild_id: int) -> SerenityGuild:
        if (guild := self.cached_guilds.get(guild_id)) is None:
            guild = await self.model_manager.get_or_create_guild(guild_id)

            self.cached_guilds[guild_id] = guild

        return guild

    async def get_or_create_user(self, user_id: int) -> SerenityUser:
        if (user := self.user_cache.get(user_id)) is None:
            user = await self.model_manager.get_or_create_user(user_id)

            # Automatically gets evicted after 30 minutes
            self.user_cache.push(user.id, user)

        return user

    @property
    def pool(self) -> Pool[Record]:
        return self._pool

    @property
    def redis(self) -> Redis[Any]:
        return self._redis

    @property
    def logger(self) -> Logger:
        return _logger

    @override
    async def start(self, *args: Any, **kwargs: Any) -> None:
        await super().start(self.config.DISCORD_TOKEN, *args, **kwargs)

    @override
    async def process_commands(self, message: discord.Message, /) -> None:
        try:
            await asyncio.wait_for(self.wait_until_ready(), timeout=5.0)
        except asyncio.TimeoutError:
            return

        ctx = await self.get_context(message)

        if ctx.command is None:
            return

        if ctx.guild:
            if not isinstance(ctx.channel, GuildMessagable) or not isinstance(
                ctx.me, discord.Member
            ):
                return

            if not ctx.channel.permissions_for(ctx.me).send_messages:
                if await self.is_owner(ctx.author):
                    await ctx.author.send(
                        "I don't have permission to send messages in that channel."
                    )

                return

        await self.invoke(ctx)

    @override
    async def connect(self, *, reconnect: bool = True) -> None:
        def _get_or_zero(obj: Any, attr: str) -> int:
            return getattr(obj, attr, 0)

        backoff = ExponentialBackoff()
        ws_params: dict[str, Any] = {
            "initial": True,
            "shard_id": getattr(self, "shard_id", None),
        }
        while not self.is_closed():
            try:
                # Here we are trying to patch the gateway connection to
                # use our own implementation using a mobile user-agent.
                coro: Any = MobileGateway.from_client(self, **ws_params)
                self.ws = await asyncio.wait_for(coro, timeout=60.0)
                ws_params["initial"] = False
                while True:
                    await self.ws.poll_event()
            except discord.client.ReconnectWebSocket as e:
                self.logger.info(
                    "Got a request to %s the websocket.",
                    getattr(e, "op", None),
                )
                self.dispatch("disconnect")

                ws_params.update(
                    sequence=self.ws.sequence,
                    resume=getattr(e, "resume", False),
                    session=self.ws.session_id,
                )
                continue
            except (
                OSError,
                discord.HTTPException,
                discord.GatewayNotFound,
                discord.ConnectionClosed,
                ClientError,
            ) as exc:
                self.dispatch("disconnect")

                if not reconnect:
                    await self.close()
                    if (
                        isinstance(exc, discord.ConnectionClosed)
                        and _get_or_zero(exc, "code") == 1000
                    ):
                        # Clean close, don't re-raise this
                        return
                    raise

                if self.is_closed():
                    return

                # If we get connection reset by peer then try to RESUME
                if isinstance(exc, OSError) and exc.errno in (54, 10054):
                    ws_params.update(
                        sequence=self.ws.sequence,
                        initial=False,
                        resume=True,
                        session=self.ws.session_id,
                    )
                    continue

                # We should only get this when an unhandled close code happens,
                # such as a clean disconnect (1000) or a bad state (bad token, no sharding, etc)
                # sometimes, discord sends us 1000 for unknown reasons so we should reconnect
                # regardless and rely on is_closed instead
                if isinstance(exc, discord.ConnectionClosed):
                    if _get_or_zero(exc, "code") == 4014:
                        raise discord.PrivilegedIntentsRequired(
                            _get_or_zero(exc, "shard_id")
                        ) from None
                    if _get_or_zero(exc, "code") != 1000:
                        await self.close()
                        raise

                retry = backoff.delay()
                self.logger.exception("Attempting a reconnect in %.2fs.", retry)
                await asyncio.sleep(retry)
                # Always try to RESUME the connection
                # If the connection is not RESUME-able then the gateway will invalidate the session.
                # This is apparently what the official Discord client does.
                ws_params.update(
                    sequence=self.ws.sequence,
                    resume=True,
                    session=self.ws.session_id,
                )

                await super().connect(reconnect=True)

    async def on_ready(self) -> None:
        self.logger.info("Logged in as %s", self.user)

        if hasattr(self, "uptime") is False:
            self.uptime = discord.utils.utcnow()

    @override
    async def close(self) -> None:
        to_close = (self.pool, self.session, self.redis)
        asyncio.gather(
            *[resource.close() for resource in to_close if resource is not None]
        )

        await super().close()

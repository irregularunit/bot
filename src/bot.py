"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
from logging import Logger, getLogger
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Iterator,
    Mapping,
    Optional,
    ParamSpec,
    Type,
    TypeVar,
)

import asyncpg
import discord
from aiohttp import ClientError
from discord.ext import commands

from bridges import PostgresBridge, RedisBridge
from gateway import Gateway
from models import Guild, ModelManager, User
from settings import Config
from utils import Context, ContextT

if TYPE_CHECKING:
    from datetime import datetime

    from aiohttp import ClientSession
    from asyncpg import Connection, Pool, Record


BotT = TypeVar("BotT", bound="Bot")
P = ParamSpec("P")
T = TypeVar("T")
API_VERSION: int = 10


class Bot(commands.Bot):
    if TYPE_CHECKING:
        user: discord.ClientUser
        cogs: Mapping[str, commands.Cog]
        start_time: datetime

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        session: ClientSession,
        pool: Pool,
        redis: RedisBridge,
    ) -> None:
        intents: discord.Intents = discord.Intents(
            guilds=True,
            members=True,
            messages=True,
            message_content=True,
            presences=True,
        )
        super().__init__(
            command_prefix=self.get_prefix,  # type: ignore
            case_insensitive=True,
            chunk_guilds_at_startup=False,
            intents=intents,
            max_messages=2000,
            owner_ids=[380067729400528896],
            help_command=commands.MinimalHelpCommand(),
        )
        self.loop: asyncio.AbstractEventLoop = loop
        self.session: ClientSession = session
        self.pool: Pool = pool
        self.redis: RedisBridge = redis

        self.config: Config = Config()  # type: ignore (my IDE doesn't get it)
        self.logger: Logger = getLogger(__name__)
        self.safe_connection: PostgresBridge = PostgresBridge(self.pool)
        self.manager: ModelManager = ModelManager(self.pool)

        self.cached_users: dict[int, User] = {}
        self.cached_guilds: dict[int, Guild] = {}
        self.cached_prefixes: dict[int, re.Pattern] = {}

    @staticmethod
    @discord.utils.copy_doc(asyncio.to_thread)
    async def to_thread(func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    async def get_context(self, message: discord.Message, *, cls: Type[ContextT] = Context) -> Context:
        return await super().get_context(message, cls=cls or commands.Context["Bot"])

    async def process_commands(self, message: discord.Message, /) -> None:
        try:
            await asyncio.wait_for(self.wait_until_ready(), timeout=5.0)
        except asyncio.TimeoutError:
            return

        ctx: Context = await self.get_context(message, cls=Context)

        if ctx.command is None:
            return

        if ctx.guild:
            assert isinstance(ctx.channel, (discord.TextChannel, discord.Thread))

            if not ctx.channel.permissions_for(ctx.me).send_messages:  # type: ignore
                if await self.is_owner(ctx.author):
                    await ctx.send(f"I cannot send messages in {ctx.channel.name}.")

                return

        await self.invoke(ctx)

    async def get_prefix(self, message: discord.Message) -> str | list[str]:
        prefixes: list[str] = [f"<@!{self.user.id}> ", f"<@{self.user.id}> ", "uwu ", "uwu"]
        if message.guild is None:
            # We're in a DM, which generally shouldn't happen. But
            # the type checker doesn't get that, so we have to do this.
            escaped_prefixes: list[str] = list(map(re.escape, prefixes))
            if match := re.match(fr"^(?:{'|'.join(escaped_prefixes)})\s*", message.content):
                return match.group()
            return commands.when_mentioned_or(*prefixes)(self, message)

        if message.guild.id not in self.cached_prefixes:
            # We're caching the Pattern object because it's faster than
            # fetching and recompiling the prefixes every time.
            guild: Guild = await self.manager.get_or_create_guild(message.guild.id)
            pattern: re.Pattern[str] = re.compile(fr"^(?:{'|'.join(map(re.escape, guild.prefixes))})\s*")
            self.cached_prefixes[message.guild.id] = pattern

        if match := self.cached_prefixes[message.guild.id].match(message.content):
            return match.group()

        return commands.when_mentioned_or(*prefixes)(self, message)

    @classmethod
    @discord.utils.copy_doc(asyncpg.create_pool)
    async def create_pool(cls: Type[BotT], *, dsn: str, **kwargs: Any) -> Optional[Pool[Record]]:
        prep_init: Any | None = kwargs.pop("init", None)

        async def init(connection: Connection[Any]) -> None:
            await connection.set_type_codec(
                "jsonb",
                encoder=lambda obj: discord.utils._to_json(obj),
                decoder=lambda data: discord.utils._from_json(data),
                schema="pg_catalog",
                format="text",
            )
            if prep_init:
                await prep_init(connection)

        return await asyncpg.create_pool(dsn=dsn, init=init, **kwargs)

    async def connect(self, *, reconnect: bool = True) -> None:
        backoff = discord.client.ExponentialBackoff()  # type: ignore
        ws_params: dict[str, Any] = {"initial": True, "shard_id": self.shard_id}
        while not self.is_closed():
            try:
                # Here we are trying to patch the gateway connection to
                # use our own implementation using a mobile user-agent.
                coro: Any = Gateway.from_client(self, **ws_params)
                self.ws = await asyncio.wait_for(coro, timeout=60.0)
                ws_params["initial"] = False
                while True:
                    await self.ws.poll_event()
            except discord.client.ReconnectWebSocket as e:
                self.logger.info("Got a request to %s the websocket.", e.op)
                self.dispatch("disconnect")
                ws_params.update(
                    sequence=self.ws.sequence,
                    resume=e.resume,
                    session=self.ws.session_id,
                )
                continue
            except (
                OSError,
                discord.HTTPException,
                discord.GatewayNotFound,
                discord.ConnectionClosed,
                ClientError,
                asyncio.TimeoutError,
            ) as exc:
                self.dispatch("disconnect")
                if not reconnect:
                    await self.close()
                    if isinstance(exc, discord.ConnectionClosed) and exc.code == 1000:
                        # clean close, don't re-raise this
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
                    if exc.code == 4014:
                        raise discord.PrivilegedIntentsRequired(exc.shard_id) from None
                    if exc.code != 1000:
                        await self.close()
                        raise

                retry: float = backoff.delay()
                self.logger.exception("Attempting a reconnect in %.2fs.", retry)
                await asyncio.sleep(retry)
                # Always try to RESUME the connection
                # If the connection is not RESUME-able then the gateway will invalidate the session.
                # This is apparently what the official Discord client does.
                ws_params.update(sequence=self.ws.sequence, resume=True, session=self.ws.session_id)

    async def start(self, *args: Any, **kwargs: Any) -> None:
        await super().start(token=self.config.token, *args, **kwargs)

    @staticmethod
    def chunker(item: str, *, size: int = 2000) -> Generator[str, None, None]:
        for i in range(0, len(item), size):
            yield item[i : i + size]

    def iter_extensions(self) -> Iterator[str]:
        extension: list[str] = [file for file in os.listdir("src/modules") if not file.startswith("_")]
        for file in extension:
            yield f"modules.{file[:-3] if file.endswith('.py') else file}"

    def iter_schemas(self) -> Iterator[pathlib.Path]:
        root: pathlib.Path = pathlib.Path("src/schemas")
        for schema in root.glob("*.sql"):
            # Ignore nasty hidden files
            if schema.name.startswith("_"):
                continue

            yield schema  # Returns the PosixPath object (assuming we don't use Windows)

    async def setup_hook(self) -> None:
        _log: Logger = self.logger.getChild("setup_hook")
        for item in list(self.iter_extensions()) + list(self.iter_schemas()):
            marked_as: str = "extension" if isinstance(item, str) else "schema"
            try:
                # Honestly, Idk why I made it like this
                if isinstance(item, str):
                    await self.load_extension(item)
                elif isinstance(item, pathlib.Path):
                    await self.pool.execute(item.read_text())
                else:
                    _log.exception(f"Expected {item!r} to be a string or a Path, got {type(item)!r}")
                    continue

                _log.info(f"Loaded {marked_as} {item!r}")
            except Exception as exc:
                _log.exception(f"Failed to load {marked_as} {item!r}", exc_info=exc)

        await self.redis.connect()

        self.cached_guilds = await self.manager.get_all_guilds()
        self.cached_users = await self.manager.get_all_users()

    async def on_ready(self) -> None:
        if not getattr(self, "start_time", None):
            self.start_time = discord.utils.utcnow()

        self.logger.getChild("on_ready").info("Connected to Discord.")

    async def close(self) -> None:
        to_close: list[Any] = [self.pool, self.session, self.redis]
        await asyncio.gather(*[c.close() for c in to_close if c is not None])
        await super().close()

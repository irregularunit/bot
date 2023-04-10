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
import random
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
from discord.ext import commands, tasks
from typing_extensions import override

from bridges import RedisBridge
from gateway import Gateway
from models import Guild, ModelManager, User
from settings import Config
from utils import Context, ContextT, GuildMessageable, MinimalisticHelpCommand

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

    @override
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
            help_command=MinimalisticHelpCommand(),
        )
        self.loop: asyncio.AbstractEventLoop = loop
        self.session: ClientSession = session
        self.pool: Pool = pool
        self.redis: RedisBridge = redis

        self.config: Config = Config()  # type: ignore (my IDE doesn't get it)
        self.logger: Logger = getLogger(__name__)
        self.manager: ModelManager = ModelManager(self.pool)

        self.cached_users: dict[int, User] = {}
        self.cached_guilds: dict[int, Guild] = {}
        self.cached_prefixes: dict[int, re.Pattern] = {}

        self.update_presence.start()

    @staticmethod
    @discord.utils.copy_doc(asyncio.to_thread)
    async def to_thread(
        func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs
    ) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    @override
    async def get_context(
        self, message: discord.Message, *, cls: Type[ContextT] = Context
    ) -> Context:
        return await super().get_context(
            message, cls=cls or commands.Context["Bot"]
        )

    async def process_commands(self, message: discord.Message, /) -> None:
        try:
            await asyncio.wait_for(self.wait_until_ready(), timeout=5.0)
        except asyncio.TimeoutError:
            return

        ctx: Context = await self.get_context(message, cls=Context)

        if ctx.command is None:
            return

        if ctx.guild:
            if not isinstance(ctx.channel, GuildMessageable):
                return

            if not ctx.channel.permissions_for(ctx.me).send_messages:  # type: ignore
                if await self.is_owner(ctx.author):
                    await ctx.send(
                        f"I cannot send messages in {ctx.channel.name}."
                    )

                return

        await self.invoke(ctx)

    @override
    async def get_prefix(self, message: discord.Message) -> str | list[str]:
        prefixes: tuple[str, ...] = (
            f"<@!{self.user.id}> ",
            f"<@{self.user.id}> ",
        )
        if message.guild is None:
            # No dm's :3
            raise commands.NoPrivateMessage()

        if message.guild.id not in self.cached_prefixes:
            guild: Guild = await self.manager.get_or_create_guild(
                message.guild.id
            )
            pattern: re.Pattern[str] = re.compile(
                r"|".join(
                    re.escape(prefix) + r"\s*" for prefix in guild.prefixes
                ),
                re.IGNORECASE,
            )

            self.cached_prefixes[message.guild.id] = pattern

        if match := self.cached_prefixes[message.guild.id].match(
            message.content
        ):
            return match.group()

        # Fallback, but it shouldn't be needed
        return commands.when_mentioned_or(*prefixes)(self, message)

    @classmethod
    @discord.utils.copy_doc(asyncpg.create_pool)
    async def create_pool(
        cls: Type[BotT], *, dsn: str, **kwargs: Any
    ) -> Optional[Pool[Record]]:
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

    @override
    async def connect(self, *, reconnect: bool = True) -> None:
        backoff = discord.client.ExponentialBackoff()  # type: ignore
        ws_params: dict[str, Any] = {
            "initial": True,
            "shard_id": self.shard_id,
        }
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
                OSError,  # This inclused (TimeoutError)
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
                        and exc.code == 1000
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
                    if exc.code == 4014:
                        raise discord.PrivilegedIntentsRequired(
                            exc.shard_id
                        ) from None
                    if exc.code != 1000:
                        await self.close()
                        raise

                retry: float = backoff.delay()
                self.logger.exception(
                    "Attempting a reconnect in %.2fs.", retry
                )
                await asyncio.sleep(retry)
                # Always try to RESUME the connection
                # If the connection is not RESUME-able then the gateway will invalidate the session.
                # This is apparently what the official Discord client does.
                ws_params.update(
                    sequence=self.ws.sequence,
                    resume=True,
                    session=self.ws.session_id,
                )

    @override
    async def start(self, *args: Any, **kwargs: Any) -> None:
        await super().start(token=self.config.token, *args, **kwargs)

    @staticmethod
    def chunker(item: str, *, size: int = 2000) -> Generator[str, None, None]:
        for i in range(0, len(item), size):
            yield item[i : i + size]

    @staticmethod
    def iter_extensions() -> Iterator[str]:
        extension: list[str] = [
            file
            for file in os.listdir("src/modules")
            if not file.startswith("_")
        ]
        for file in extension:
            yield f"modules.{file[:-3] if file.endswith('.py') else file}"

    @staticmethod
    def iter_schemas() -> Iterator[pathlib.Path]:
        root: pathlib.Path = pathlib.Path("src/schemas")
        for schema in root.glob("*.sql"):
            # Ignore nasty hidden files
            if schema.name.startswith("_"):
                continue

            yield schema  # Returns the PosixPath object (assuming we don't use Windows)

    @override
    async def setup_hook(self) -> None:
        _log: Logger = self.logger.getChild("setup_hook")

        initial_exts: list[str] = list(self.iter_extensions())
        initial_schemas: list[pathlib.Path] = list(self.iter_schemas())

        errors = await asyncio.gather(
            *[self.load_extension(ext) for ext in initial_exts],
            *[
                self.pool.execute(schema.read_text())
                for schema in initial_schemas
            ],
        )

        for ext, error in zip(initial_exts, errors):
            if error:
                _log.exception(
                    f"Failed to load extension {ext!r}", exc_info=error
                )
            else:
                _log.info(f"Loaded extension {ext!r}")

        for schema, error in zip(initial_schemas, errors):
            if error:
                _log.exception(
                    f"Failed to load schema {schema!r}", exc_info=error
                )
            else:
                _log.info(f"Loaded schema {schema!r}")

        await self.redis.connect()

        self.cached_guilds = await self.manager.get_all_guilds()
        self.cached_users = await self.manager.get_all_users()

    async def on_ready(self) -> None:
        if not getattr(self, "start_time", None):
            self.start_time = discord.utils.utcnow()

        self.logger.getChild("on_ready").info(
            "Successfully connected to Discord with %s as %s",
            self.user,
            self.user.id,
        )

    @tasks.loop(minutes=15)
    async def update_presence(self) -> None:
        presences: dict[discord.ActivityType, str] = {
            discord.ActivityType.watching: (
                f"over {len(self.guilds)} {'guilds' if len(self.guilds) != 1 else 'guild'}"
            ),
            discord.ActivityType.listening: f"to {len(self.users)} {'users' if len(self.users) != 1 else 'user'}",
            discord.ActivityType.playing: (
                f"with {len(self.commands)} {'commands' if len(self.commands) != 1 else 'command'}"
            ),
        }

        activity_type, message = random.choice(list(presences.items()))
        await self.change_presence(
            activity=discord.Activity(type=activity_type, name=message)
        )

    @update_presence.before_loop
    async def before_presence(self) -> None:
        await self.wait_until_ready()

    @override
    async def close(self) -> None:
        to_close: list[Any] = [self.pool, self.session, self.redis]

        async with asyncio.TaskGroup() as group:
            for c in to_close:
                if c is None:
                    continue

                await group.create_task(c.close())

        await super().close()

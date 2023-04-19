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
from meta import (  # fmt: off; sucks that isort w. pyright settings tries; to map this into a one liner...; fmt: on
    __author__ as author,
    __license__ as license,
    __version__ as version,
)
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
    """Custom bot class for the bot.

    Parameters
    ----------
    loop : `asyncio.AbstractEventLoop`
        The event loop to use.
    session : `aiohttp.ClientSession`
        The session to use for HTTP requests.
    pool : `asyncpg.Pool`
        The pool to use for database connections.
    redis : `RedisBridge`
        The bridge to use for Redis connections.
    """

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
        pool: Pool[Record],
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
        self.pool: Pool[Record] = pool
        self.redis: RedisBridge = redis

        self.version: str = version
        self.author: str = author
        self.license: str = license

        # my IDE doesn't get it
        self.config: Config = Config()  # type: ignore
        self.logger: Logger = getLogger(__name__)
        self.manager: ModelManager = ModelManager(self.pool)

        self.cached_users: dict[int, User] = {}
        self.cached_guilds: dict[int, Guild] = {}
        self.cached_prefixes: dict[int, re.Pattern[str]] = {}

        self.update_presence.start()

    @staticmethod
    @discord.utils.copy_doc(asyncio.to_thread)
    async def to_thread(func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def chunker(item: str, *, size: int = 2000) -> Generator[str, None, None]:
        """Yield successive n-sized chunks from l.

        Parameters
        ----------
        item : `str`
            The item to chunk.
        size : `Optional[int]`
            The size of the chunks, defaults to 2000.

        Yields
        ------
        `str`
            The chunked item.
        """
        for i in range(0, len(item), size):
            yield item[i : i + size]

    @staticmethod
    def iter_extensions() -> Generator[str, None, None]:
        """Iterate over the extensions in the modules folder.

        Yields
        ------
        `str`
            The full qualified name of the extension.
        """
        extension: list[str] = [
            file for file in os.listdir("src/modules") if not file.startswith("_")
        ]
        for file in extension:
            yield f"modules.{file[:-3] if file.endswith('.py') else file}"

    @staticmethod
    def iter_schemas() -> Generator[pathlib.Path, None, None]:
        """Iterate over the schemas in the schemas folder.

        Yields
        ------
        `pathlib.Path`
            The path to the schema.
        """
        root: pathlib.Path = pathlib.Path("src/schemas")
        for schema in root.glob("*.sql"):
            # Ignore nasty hidden files
            if schema.name.startswith("_"):
                continue

            yield schema  # Returns the PosixPath object (assuming we don't use Windows)

    @override
    async def get_context(
        self, message: discord.Message | discord.Interaction, *, cls: Type[ContextT] = Context
    ) -> Context:
        """Returns the invocation context from the message or interaction.

        This is a more low-level counter-part for :meth:`.process_commands`
        to allow users more fine grained control over the processing.

        The returned context is not guaranteed to be a valid invocation
        context, `.Context.valid` must be checked to make sure it is.
        If the context is not valid then it is not a valid candidate to be
        invoked under `Bot.invoke`.

        Parameters
        ----------
        origin: `Union[discord.Message, discord.Interaction]`
            The message or interaction to get the invocation context from.
        cls
            The factory class that will be used to create the context.
            By default, this is `.Context`. Should a custom
            class be provided, it must be similar enough to `.Context`\'s
            interface.

        Returns
        -------
        `Context`
            The invocation context. The type of this can change via the
            `cls` parameter.
        """
        return await super().get_context(message, cls=cls or commands.Context["Bot"])

    async def process_commands(self, message: discord.Message, /) -> None:
        """Processes commands found in `message`.

        Parameters
        ----------
        message : `discord.Message`
            The message to process commands for.
        """
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

            # TODO: ensure the user exists in our database, prepare for grinding game

            if not ctx.channel.permissions_for(ctx.me).send_messages:  # type: ignore
                if await self.is_owner(ctx.author):
                    await ctx.send(f"I cannot send messages in {ctx.channel.name}.")

                return

        await self.invoke(ctx)

    @override
    async def get_prefix(self, message: discord.Message) -> str | list[str]:
        """Returns the prefix for the given message.

        Parameters
        ----------
        message : `discord.Message`
            The message to get the prefix for.

        Returns
        -------
        `str` | `list[str]`
            The prefix for the given message.

        Raises
        ------
        `commands.NoPrivateMessage`
            If the message is sent outside of the guild context.
        """

        if message.guild is None:
            # No dm's :3
            raise commands.NoPrivateMessage()

        if message.guild.id not in self.cached_prefixes:
            guild: Guild = await self.manager.get_or_create_guild(message.guild.id)
            if guild.prefixes[0] is not None:
                pattern: re.Pattern[str] = re.compile(
                    r"|".join(re.escape(prefix) + r"\s*" for prefix in guild.prefixes),
                    re.IGNORECASE,
                )
            else:
                pattern = re.compile(r"<@!?{0.id}>".format(self.user), re.IGNORECASE)

            self.cached_prefixes[message.guild.id] = pattern

        if match := self.cached_prefixes[message.guild.id].match(message.content):
            return match.group()

        # Fallback, but it shouldn't be needed
        return commands.when_mentioned(self, message)

    @classmethod
    @discord.utils.copy_doc(asyncpg.create_pool)
    async def create_pool(cls: Type[BotT], *, dsn: str, **kwargs: Any) -> Optional[Pool[Record]]:
        prep_init: Any | None = kwargs.pop("init", None)

        async def init(connection: Connection[Any]) -> None:
            await connection.set_type_codec(
                "jsonb",
                encoder=discord.utils._to_json,
                decoder=discord.utils._from_json,
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
                OSError,  # This includes (TimeoutError)
                discord.HTTPException,
                discord.GatewayNotFound,
                discord.ConnectionClosed,
                ClientError,
            ) as exc:
                self.dispatch("disconnect")
                if not reconnect:
                    await self.close()
                    if isinstance(exc, discord.ConnectionClosed) and exc.code == 1000:
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
                ws_params.update(
                    sequence=self.ws.sequence,
                    resume=True,
                    session=self.ws.session_id,
                )

    @override
    async def start(self, *args: Any, **kwargs: Any) -> None:
        await super().start(token=self.config.token, *args, **kwargs)

    @override
    async def setup_hook(self) -> None:
        _log: Logger = self.logger.getChild("setup_hook")

        initial_exts: list[str] = list(self.iter_extensions())
        initial_schemas: list[pathlib.Path] = list(self.iter_schemas())

        async def load_and_log(item: str | pathlib.Path) -> None:
            try:
                if isinstance(item, str):
                    await self.load_extension(item)
                    _log.info(f"Loaded extension {item!r}")
                elif isinstance(item, pathlib.Path):
                    # Only been tested with posix paths, but should work anywhere (I GUESS)
                    await self.pool.execute(item.read_text())
                    _log.info(f"Loaded schema {item!r}")

            except Exception as e:
                _log.exception(f"Failed to load {item!r}", exc_info=e)

        await asyncio.gather(*[load_and_log(item) for item in initial_exts + initial_schemas])

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
        """Updates the bot's presence in fixed intervals."""
        activity_hash_map: dict[discord.ActivityType, str] = {
            discord.ActivityType.watching: "your mom",
            discord.ActivityType.listening: "your dreams",
            discord.ActivityType.playing: "with your feelings",
        }

        activity_type, message = random.choice(list(activity_hash_map.items()))
        await self.change_presence(activity=discord.Activity(type=activity_type, name=message))

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

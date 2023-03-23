"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import datetime
import re
from logging import Logger, getLogger
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

import discord
from discord.ext import commands

from exceptions import ExceptionLevel, UserFeedbackException, UserFeedbackExceptionFactory
from models import EmbedBuilder
from utils import BaseExtension

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("DiscordErrorHandler", "Error")

log: Logger = getLogger(__name__)


class Error:
    def __init__(
        self,
        *,
        exception: Type[Exception],
        level: ExceptionLevel,
        message: str,
        **kwargs: Any,
    ) -> None:
        self.exception: Type[Exception] = exception
        self.level: ExceptionLevel = level
        self.message: str = message
        self.kwargs: Dict[str, Any] = kwargs

    def __repr__(self) -> str:
        return f"<Error {self.exception.__name__} {self.level.name} {self.message} {self.kwargs}>"

    def to_string(self) -> str:
        partial_exception = UserFeedbackExceptionFactory.create(message=self.message, level=self.level)
        return partial_exception.to_string()


class DiscordErrorHandler(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.bot: Bot = bot
        self.flyweight: Dict[str, Error] = {}

    def create_error(
        self,
        exception: Type[Exception],
        level: ExceptionLevel,
        message: str,
        **kwargs: Any,
    ) -> Error:
        if (instance := self.get_error(exception)) is not None:
            return instance

        instance = Error(exception=exception, level=level, message=message, **kwargs)
        self.flyweight[exception.__name__] = instance
        return instance

    def get_error(self, exception: Type[Exception]) -> Optional[Error]:
        return self.flyweight.get(exception.__name__, None)

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx: Context, error: Exception) -> Optional[discord.Message]:
        if hasattr(ctx.command, "on_error"):
            # The invoked command has a local error handler
            # therefore we can safely ignore this error
            return

        # Idk tbh
        if not ctx.command:
            return

        if ctx.cog:
            if ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
                # The cog which the invoked command belongs to has a local error handler
                return

        # We handle custom exceptions first
        if isinstance(error, UserFeedbackException):
            return await ctx.safe_send(content=error.to_string())

        # Gets the original exception
        exc: Any | Exception = getattr(error, "original", error)

        if isinstance(exc, commands.CommandNotFound):
            # The invoked command does not exist
            return

        if isinstance(exc, commands.NotOwner):
            return await ctx.safe_send(content="You are not the owner of this bot, so you cannot use this command.")

        if isinstance(exc, commands.CommandOnCooldown):
            if await self.bot.redis.get(f"cooldown:{ctx.author.id}") is not None:
                # The user is most likely spamming the bot,
                # trying to ratelimit it I've decided to not
                # send a message in that case to avoid further API calls
                return

            await self.bot.redis.setex(f"cooldown:{ctx.author.id}", 5, exc.retry_after)

            time_counter = self.to_discord_time_format(exc.retry_after)
            return await ctx.safe_send(
                content=f"⏱ | You are on cooldown, try again in {time_counter}.", delete_after=exc.retry_after + 1
            )

        if isinstance(exc, commands.TooManyArguments):
            # maybe add better error handling later?
            return await ctx.send_help(ctx.command)

        if isinstance(exc, commands.MissingRequiredArgument):
            return await self.handle_missing_required_argument(ctx, exc)

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.safe_send(content="Ion do dm's.")

        if isinstance(error, commands.MemberNotFound):
            return await ctx.safe_send(content=f"Could not find a user with the name `{error.argument}`.")

        if isinstance(error, commands.BadArgument):
            return await self.handle_bad_argument(ctx, error)

        if isinstance(error, commands.MissingPermissions):
            return await ctx.safe_send(content="You do not have the required permissions to use this command.")

        if isinstance(error, commands.BotMissingPermissions):
            # I don't care about this error tbh, config error on
            # the user's side, :shrug:
            return

        log.getChild("on_command_error").exception(
            f"Unhandled exception in command {ctx.command.qualified_name}", exc_info=exc
        )

    def to_discord_time_format(self, seconds: Union[int, float]) -> str:
        time = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        return discord.utils.format_dt(time, style="R")

    async def handle_missing_required_argument(
        self, ctx: Context, error: commands.MissingRequiredArgument
    ) -> Optional[discord.Message]:
        assert ctx.command is not None

        command = ctx.command
        signature = command.signature
        missing_argument = error.param.name

        error_message = ' '.join(
            f"{'^' if param.replace('[', '').replace(']', '') == missing_argument else ' '}{param}"
            for param in signature.split()
            if param != '*'
        )
        command_usage = f"{command.name} {error_message}"

        lineo = command.callback.__code__.co_firstlineno
        embed_description = f"""```sh
        error: missing required argument {missing_argument}
           --> $ext/{command.cog.qualified_name.lower()}.py:{lineo}
             |
        {lineo}  | {command_usage}
             |
             |
             | => For more information use help {command.qualified_name}
        ```"""
        embed_description = re.sub(r"^ {8}", "", embed_description, flags=re.MULTILINE)

        return await ctx.safe_send(
            embed=EmbedBuilder.factory(ctx, title="Required argument was missing!", description=embed_description)
        )

    async def handle_bad_argument(self, ctx: Context, error: commands.BadArgument) -> Optional[discord.Message]:
        assert ctx.command is not None

        error_lineno = ctx.command.callback.__code__.co_firstlineno

        information = "Error: Bad argument passed\n"
        about = f" --> $ext/{ctx.command.qualified_name.lower()}.py:{error_lineno}:{error_lineno + 1}\n"
        designer = " | "

        error_message_parts = error.args[0].split("\n")
        error_message = f"```\n{information}{about}\n"

        for part in error_message_parts:
            error_message += f"{designer}{part}\n"
        error_message += f"{designer}\n"
        error_message += f"{designer} => pls help {ctx.command.name}```"

        embed = EmbedBuilder.factory(
            ctx, title="Oh no! You've encountered an error!", description=error_message, timestamp=ctx.message.created_at
        )
        embed.set_footer(text=f"Invoked by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        return await ctx.maybe_reply(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(DiscordErrorHandler(bot))

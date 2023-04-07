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
    __slots__: tuple[str, ...] = ("exception", "level", "message", "kwargs")

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
        self.bot: Bot = bot
        self.flyweight: Dict[str, Error] = {}

    @staticmethod
    def to_discord_time_format(seconds: Union[int, float]) -> str:
        time = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        return discord.utils.format_dt(time, style="R")

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
            if not (err := self.get_error(commands.NotOwner)):
                err = self.create_error(
                    exception=commands.NotOwner,
                    level=ExceptionLevel.ERROR,
                    message="You are not the owner of this bot, so you cannot use this command.",
                )
                return await ctx.safe_send(content=err.to_string())

            return await ctx.safe_send(content=err.to_string())

        if isinstance(exc, commands.CommandOnCooldown):
            if await self.bot.redis.client.get(f"cooldown:{ctx.author.id}") is not None:
                return

            await self.bot.redis.client.setex(
                name=f"cooldown:{ctx.author.id}",
                value="1",
                time=int(exc.retry_after) + 1,
            )

            time_counter = self.to_discord_time_format(exc.retry_after)
            return await ctx.safe_send(
                content=f":stopwatch: | You are on cooldown, try again in {time_counter}.",
                delete_after=exc.retry_after + 1,
            )

        if isinstance(exc, commands.TooManyArguments):
            # Maybe add better error handling later?
            return await ctx.send_help(ctx.command)

        if isinstance(exc, commands.MissingRequiredArgument):
            arg = exc.param.name
            signature = ctx.command.signature
            full_qualified_signature = ctx.command.full_parent_name + ctx.command.qualified_name

            partial_exception = UserFeedbackExceptionFactory.create(
                message=(
                    f"Missing required argument `{arg}`.\n"
                    f"{self.bot.config.blank_emote} **|** Usage: `{ctx.prefix}{full_qualified_signature} {signature}`"
                ),
                level=ExceptionLevel.ERROR,
            )
            return await ctx.safe_send(content=partial_exception.to_string())

        if isinstance(error, commands.NoPrivateMessage):
            if not (err := self.get_error(commands.NoPrivateMessage)):
                err = self.create_error(
                    exception=commands.NoPrivateMessage,
                    level=ExceptionLevel.ERROR,
                    message="Ion do dm's.",
                )
                return await ctx.safe_send(content=err.to_string())

            return await ctx.safe_send(content=err.to_string())

        if isinstance(error, commands.MemberNotFound):
            return await ctx.safe_send(content=f"Could not find a user with the name `{error.argument}`.")

        if isinstance(error, commands.BadArgument):
            partial_exception = UserFeedbackExceptionFactory.create(message=str(error), level=ExceptionLevel.ERROR)
            return await ctx.safe_send(content=partial_exception.to_string())

        if isinstance(error, commands.MissingPermissions):
            if not (err := self.get_error(commands.MissingPermissions)):
                err = self.create_error(
                    exception=commands.MissingPermissions,
                    level=ExceptionLevel.WARNING,
                    message="You do not have the required permissions to use this command.",
                )
                return await ctx.safe_send(content=err.to_string())

            return await ctx.safe_send(content=err.to_string())

        if isinstance(error, commands.BotMissingPermissions):
            # I don't care about this error tbh, config error on
            # the user's side, not on our end.
            log.getChild("on_command_error").warning(
                f"Bot is missing permissions to run command {ctx.command.qualified_name} in\n"
                f"Guild: {ctx.guild.name} ({ctx.guild.id}) at {ctx.channel} ({ctx.channel.id})"
            )
            return

        log.getChild("on_command_error").exception(
            f"Unhandled exception in command {ctx.command.qualified_name}", exc_info=exc
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(DiscordErrorHandler(bot))

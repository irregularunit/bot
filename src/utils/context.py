"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import copy
import io
import re
from logging import Logger, getLogger
from typing import TYPE_CHECKING, Any, Literal, Optional, Self, TypeVar

import discord
from discord.ext import commands
from typing_extensions import override

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from src.bot import Bot

__all__: tuple[str, ...] = ("Context", "ContextT")

log: Logger = getLogger(__name__)
ContextT = TypeVar("ContextT", bound="Context")


class Context(commands.Context["Bot"]):
    """A class to represent a custom context."""

    if TYPE_CHECKING:
        bot: Bot
        message: discord.Message
        guild: discord.Guild

    @property
    @override
    def clean_prefix(self) -> str:
        """The prefix with the bot's name replaced with a mention.

        Returns
        -------
        `str`
            The prefix with the bot's name replaced with a mention.
        """
        repl: str = f"@{self.me.display_name}".replace("\\", r"\\")
        pattern: re.Pattern[str] = re.compile(rf" < @!?{self.me.id}>")

        if self.prefix is None:
            raise AssertionError
        return pattern.sub(repl, self.prefix)

    @property
    def reference(self) -> discord.Message | Literal[False] | None:
        """The message that was referenced in the command invocation.

        Returns
        -------
        `discord.Message | Literal[False] | None`
            The message that was referenced in the command invocation.
        """
        message: Any | None = getattr(self.message, "reference", None)
        return isinstance(message, discord.Message) and message or None

    @property
    def referenced_user(
        self,
    ) -> discord.Member | discord.User | Literal[False]:
        """The user that was referenced in the command invocation.

        Returns
        -------
        `discord.Member | discord.User | Literal[False]`
            The user that was referenced in the command invocation.
        """
        return isinstance(self.reference, discord.Message) and self.reference.author

    @property
    def session(self) -> ClientSession:
        """The bot's aiohttp session.

        Returns
        -------
        `aiohttp.ClientSession`
            The bot's aiohttp session.
        """
        return self.bot.session

    @override
    async def send_help(self, command: Optional[commands.Command | str] = None) -> None:
        """Sends the help command for the given command.

        Parameters
        ----------
        command: `Optional[commands.Command | str]`
            The command to send the help for.
        """

        # Opinionated choice that the help should default to the current command
        # why discord.py doesn't do this is beyond me
        command = command or self.command
        await super().send_help(command)

    async def safe_send(self, content: str = "", **kwargs: Any) -> Optional[discord.Message]:
        """Sends a message, splitting it into multiple messages if necessary.

        Parameters
        ----------
        content: `str`
            The content of the message.
        **kwargs: `Any`
            The keyword arguments to pass to `discord.abc.Messageable.send`.

        Returns
        -------
        `Optional[discord.Message]`
            The message that was sent.
        """
        if kwargs.pop("file", None):
            # Could add the `resize_to_limit` method here, but I don't think it's worth it
            raise RuntimeError("Files are incompatible with safe_send.")

        if len(content) <= 2000:
            return await self.send(content, **kwargs)

        fp = io.BytesIO(content.encode("utf-8"))
        return await self.send(file=discord.File(fp, filename="response.txt"), **kwargs)

    async def maybe_reply(
        self,
        content: Optional[str] = None,
        mention_author: bool = False,
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        """Sends a message, replying to the message that invoked the command if possible.

        Parameters
        ----------
        content: `Optional[str]`
            The content of the message.
        mention_author: `bool`
            Whether to mention the author of the message that invoked the command.
        **kwargs: `Any`
            The keyword arguments to pass to `discord.abc.Messageable.send`.

        Returns
        -------
        `Optional[discord.Message]`
            The message that was sent.
        """
        resolved_message: discord.Message | discord.DeletedReferencedMessage | None = (
            self.message.reference and self.message.reference.resolved
        )
        if isinstance(resolved_message, discord.DeletedReferencedMessage):
            # *pat pat* :>
            resolved_message = None
        try:
            return await (resolved_message.reply if resolved_message else self.send)(
                content=content or "", mention_author=mention_author, **kwargs
            )
        except discord.HTTPException:
            return None

    async def copy_with(self, *, author=None, channel=None, **kwargs) -> Self:
        msg: discord.Message = copy.copy(self.message)
        msg._update(kwargs)  # type: ignore

        if author is not None:
            msg.author = author
        if channel is not None:
            msg.channel = channel

        msg.content = kwargs["content"]
        return await self.bot.get_context(msg, cls=type(self))

# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import re
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands
from typing_extensions import override

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from src.models.serenity import Serenity

__all__: tuple[str, ...] = ("SerenityContext",)


class SerenityContext(commands.Context["Serenity"]):
    bot: Serenity
    prefix: str
    message: discord.Message

    async def maybe_reply(
        self,
        content: Optional[str] = None,
        mention_author: bool = False,
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        resolved_message = self.message.reference and getattr(
            self.message.reference, "resolved", None
        )

        if isinstance(resolved_message, discord.DeletedReferencedMessage):
            resolved_message = None
        try:
            return await (
                resolved_message.reply if resolved_message else self.message.reply
            )(content, mention_author=mention_author, **kwargs)
        except discord.HTTPException:
            self.bot.logger.debug(
                "Failed to reply to message %d to user %d.",
                self.message.id,
                self.message.author.id,
            )
            return None

    @property
    @override
    def clean_prefix(self) -> str:
        if not isinstance(self.me, (discord.Member, discord.User)):
            raise AssertionError("Type check failed for self.me.")

        repl = f"@{self.me.display_name}".replace("\\", r"\\")
        pattern = re.compile(rf" < @!?{self.me.id}>")

        return pattern.sub(repl, self.prefix)

    @property
    def session(self) -> ClientSession:
        return self.bot.session

    @override
    async def send_help(
        self,
        command: Optional[commands.Command[Any, Any, Any]] = None,
        *args: Any,
    ) -> None:
        command = command or getattr(self, "command", None)
        await super().send_help(command, *args)

    async def safe_send(
        self, content: str = "", **kwargs: Any
    ) -> Optional[discord.Message]:
        if kwargs.pop("file", None) is not None:
            raise ValueError("Files are incompatible with safe_send.")

        if len(content) <= 2000:
            return await self.send(content, **kwargs)

        fp = io.BytesIO(content.encode("utf-8"))
        return await self.send(file=discord.File(fp, filename="response.txt"), **kwargs)

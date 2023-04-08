"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("MemberConverter", "EmojiConverter")
custom_emoji: re.Pattern[str] = re.compile(
    r"<(?P<a>a)?:(?P<name>[a-zA-Z0-9_~]{1,}):(?P<id>[0-9]{15,19})>"
)


class MemberConverter(commands.Converter[discord.Member]):
    """A case-insensitive member converter that allows for partial matches."""

    async def convert(
        self, ctx: Context, argument: str
    ) -> Optional[discord.Member]:
        try:
            member: discord.Member = await commands.MemberConverter().convert(
                ctx, argument
            )
            return member
        except commands.MemberNotFound:
            members: list[discord.Member] = await ctx.guild.query_members(
                argument, limit=5
            )
            if not members:
                # Not even discord managed to find a member
                # partially matching the argument
                raise commands.MemberNotFound(argument)
            return members[0]


class EmojiConverter(commands.Converter[discord.PartialEmoji]):
    """Partial emoji converter, that also checks views."""

    async def from_message(
        self, ctx: Context, message: discord.Message
    ) -> Optional[list[discord.PartialEmoji]]:
        message_content: str = message.content
        for embed in message.embeds:
            for field in embed.fields:
                message_content += f"{field.name} {field.value}"

            message_content += f"{embed.title} {embed.description}"

        message_emojis: Optional[
            list[tuple[str, str, str]]
        ] = custom_emoji.findall(message_content)

        if not message_emojis:
            return None

        emojis: list[discord.PartialEmoji] = []
        for emoji in message_emojis:
            try:
                partial_emoji: discord.PartialEmoji = (
                    await commands.PartialEmojiConverter().convert(
                        ctx, f"<{emoji[0]}:{emoji[1]}:{emoji[2]}>"
                    )
                )
                emojis.append(partial_emoji)
            except commands.PartialEmojiConversionFailure:
                continue

        for component in message.components:
            if (
                isinstance(component, discord.ui.Button)
                and component.emoji is not None
            ):
                emojis.append(component.emoji)

            if isinstance(component, discord.ui.Select):
                for option in component.options:
                    if option.emoji is not None:
                        emojis.append(option.emoji)

        return emojis

    async def convert(
        self, ctx: Context, argument: Optional[str]
    ) -> Optional[list[discord.PartialEmoji]]:
        if ctx.reference:  # (False | None | discord.MessageReference)
            return await self.from_message(ctx, ctx.reference)

        emojis: list[discord.PartialEmoji] = []

        if argument is not None:
            for emoji in argument.split():
                try:
                    partial_emoji: discord.PartialEmoji = (
                        await commands.PartialEmojiConverter().convert(
                            ctx, emoji
                        )
                    )
                    emojis.append(partial_emoji)
                except commands.PartialEmojiConversionFailure:
                    continue

        if not emojis:
            async for message in ctx.channel.history(limit=10):
                maybe_found: list[
                    discord.PartialEmoji
                ] | None = await self.from_message(ctx, message)
                if maybe_found:
                    emojis.extend(maybe_found)

                if len(emojis) >= 25:
                    break

        return emojis

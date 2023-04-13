"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands
from typing_extensions import override

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("MemberConverter", "EmojiConverter")
_CUSTOM_EMOJI_REGEX: re.Pattern[str] = re.compile(
    r"<(?P<a>a)?:(?P<name>[a-zA-Z0-9_~]{1,}):(?P<id>[0-9]{15,19})>"
)
_ID_REGEX = re.compile(r'([0-9]{15,20})$')


def get_from_guilds(bot: Bot, getter: str, argument: Any) -> Any:
    result = None
    for guild in bot.guilds:
        result = getattr(guild, getter)(argument)
        if result:
            return result
    return result


class MemberConverter(commands.Converter[discord.Member]):
    """Converter that converts to discord.Member.

    All lookups are via the local guild. If in a DM context, then the lookup
    is done by the global cache.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    5. Lookup by nickname

    If the lookup fails, then a UserFeedbackException is raised.
    """

    @staticmethod
    def get_id_match(argument):
        return _ID_REGEX.match(argument)

    @staticmethod
    async def query_member_named(
        guild: discord.Guild, argument: str
    ) -> Optional[discord.Member]:
        cache = guild._state.member_cache_flags.joined
        if len(argument) > 5 and argument[-5] == '#':
            username, _, discriminator = argument.rpartition('#')
            members = await guild.query_members(
                username, limit=100, cache=cache
            )
            return discord.utils.get(
                members, name=username, discriminator=discriminator
            )

        members = await guild.query_members(argument, limit=100, cache=cache)
        return discord.utils.find(
            lambda m: argument in (m.name, m.nick), members
        )

    @staticmethod
    async def query_member_by_id(
        bot: Bot, guild: discord.Guild, user_id: int
    ) -> Optional[discord.Member]:
        ws = bot._get_websocket(shard_id=guild.shard_id)
        cache = guild._state.member_cache_flags.joined
        if ws.is_ratelimited():
            # If we're being rate limited on the WS, then fall back to using the HTTP API
            # So we don't have to wait ~60 seconds for the query to finish
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                return None

            if cache:
                guild._add_member(member)
            return member

        # If we're not being rate limited then we can use the websocket to actually query
        members = await guild.query_members(
            limit=1, user_ids=[user_id], cache=cache
        )
        if not members:
            return None
        return members[0]

    @override
    async def convert(self, ctx: Context, argument: str) -> discord.Member:
        bot = ctx.bot
        match = self.get_id_match(argument) or re.match(
            r'<@!?([0-9]{15,20})>$', argument
        )
        guild = ctx.guild
        result = None
        user_id = None

        if match is None:
            # Not a mention...
            if guild:
                result = guild.get_member_named(argument)
            else:
                result = get_from_guilds(bot, 'get_member_named', argument)
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id) or discord.utils.get(
                    ctx.message.mentions, id=user_id
                )
            else:
                result = get_from_guilds(bot, 'get_member', user_id)

        if not isinstance(result, discord.Member):
            if guild is None:
                raise UserFeedbackExceptionFactory.create(
                    f"Could not find member `{argument}` in any guild.",
                    ExceptionLevel.ERROR,
                )

            if user_id is not None:
                result = await self.query_member_by_id(bot, guild, user_id)
            else:
                result = await self.query_member_named(guild, argument)

            if not result:
                raise UserFeedbackExceptionFactory.create(
                    f"Could not find member `{argument}` in guild `{guild.name}`.",
                    ExceptionLevel.ERROR,
                )

        return result


class EmojiConverter(commands.Converter[discord.PartialEmoji]):
    """Partial emoji converter, that also checks views."""

    @staticmethod
    async def from_message(
        ctx: Context, message: discord.Message
    ) -> Optional[list[discord.PartialEmoji]]:
        message_content: str = message.content
        for embed in message.embeds:
            for field in embed.fields:
                message_content += f"{field.name} {field.value}"

            message_content += f"{embed.title} {embed.description}"

        message_emojis: Optional[
            list[tuple[str, str, str]]
        ] = _CUSTOM_EMOJI_REGEX.findall(message_content)

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
                if component.emoji.is_unicode_emoji():
                    continue

                emojis.append(component.emoji)

            if isinstance(component, discord.ui.Select):
                for option in component.options:
                    if option.emoji is not None:
                        if option.emoji.is_unicode_emoji():
                            continue

                        emojis.append(option.emoji)

        for reaction in message.reactions:
            if reaction.is_custom_emoji():
                if isinstance(reaction.emoji, discord.PartialEmoji):
                    emojis.append(reaction.emoji)

        return emojis

    @override
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

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
# pyright: reportPrivateUsage=false

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands
from typing_extensions import override

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity

__all__: tuple[str, ...] = ("MaybeMemberConverter",)

CUSTOM_EMOJI_REGEX: re.Pattern[str] = re.compile(
    r"<(?P<a>a)?:(?P<name>[a-zA-Z0-9_~]{1,}):(?P<id>[0-9]{15,19})>")
ID_REGEX = re.compile(r'([0-9]{15,20})$')


def get_from_guilds(bot: Serenity, getter: str, argument: Any) -> Any:
    result = None
    for guild in bot.guilds:
        result = getattr(guild, getter)(argument)
        if result:
            return result
    return result


class MaybeMemberConverter(commands.Converter[discord.Member]):
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
    def get_id_match(argument: str) -> Optional[re.Match[str]]:
        """Returns the ID match object or None if not found."""
        return ID_REGEX.match(argument)

    @staticmethod
    async def query_member_named(guild: discord.Guild, argument: str) -> Optional[discord.Member]:
        """Queries a member by name and discriminator.

        Parameters
        ----------
        guild: `discord.Guild`
            The guild to query.
        argument: `str`
            The name and discriminator to query.

        Returns
        -------
        `Optional[discord.Member]`
            The member found, or None if not found.
        """
        cache = guild._state.member_cache_flags.joined
        if len(argument) > 5 and argument[-5] == '#':
            username, _, discriminator = argument.rpartition('#')
            members = await guild.query_members(username, limit=100, cache=cache)
            return discord.utils.get(members, name=username, discriminator=discriminator)

        members = await guild.query_members(argument, limit=100, cache=cache)
        maybre_result = discord.utils.find(
            lambda m: argument in (m.name, m.nick), members)
        return maybre_result or members[0] if members else None

    @staticmethod
    async def query_member_by_id(bot: Serenity, guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
        """Queries a member by ID.

        Parameters
        ----------
        bot: `Bot`
            The bot instance.
        guild: `discord.Guild`
            The guild to query.
        user_id: `int`
            The ID to query.

        Returns
        -------
        `Optional[discord.Member]`
            The member found, or None if not found.
        """
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
        members = await guild.query_members(limit=5, user_ids=[user_id], cache=cache)
        if not members:
            return None

        return members[0]

    @override
    # type: ignore[override]
    async def convert(self, ctx: SerenityContext, argument: str) -> discord.Member:
        from src.shared import ExceptionFactory

        """Converts to a discord.Member.

        Parameters
        ----------
        ctx: `Context`
            The context of the command.
        argument: `str`
            The argument to convert.

        Returns
        -------
        `discord.Member`
            The member found.

        Raises
        ------
        `UserFeedbackException`
            If the member could not be found.
        """
        bot = ctx.bot
        match = self.get_id_match(argument) or re.match(
            r'<@!?([0-9]{15,20})>$', argument)
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
                    ctx.message.mentions, id=user_id)
            else:
                result = get_from_guilds(bot, 'get_member', user_id)

        if not isinstance(result, discord.Member):
            if guild is None:
                raise ExceptionFactory.create_warning_exception(
                    f"Could not find member `{argument}` in any guild.",
                )

            if user_id is not None:
                result = await self.query_member_by_id(bot, guild, user_id)
            else:
                result = await self.query_member_named(guild, argument)

            if not result:
                raise ExceptionFactory.create_warning_exception(
                    f"Could not find member `{argument}` in guild `{guild.name}`.",
                )

        return result

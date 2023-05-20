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
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from typing_extensions import override

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity

__all__: tuple[str, ...] = ("MaybeMemberConverter",)


ID_REGEX = re.compile(r'([0-9]{15,20})$')


class MaybeMemberConverter(commands.Converter[discord.Member]):
    """A converter that handles the conversion of input arguments into `discord.Member` objects.

    Notes
    -----
    The order of strategies used for looking up guild usernames is as follows:

    1. If the input argument matches the user ID format ("<@!user_id>"), it attempts to find a member
       using the guild's `get_member()` method and checks the mentioned users in the message.
    2. If the input argument contains a discriminator ("username#discriminator"), it queries the guild members
       by username and discriminator using `guild.query_members()` and searches for an exact match.
    3. Otherwise, it queries the guild members by name or nickname using `guild.query_members()`
       and searches for a partial match.

    If none of the strategies succeed in finding a member, an user feedback exception is raised.

    Parameters
    ----------
    ctx: `SerenityContext`
        The context of the command invocation that triggered this converter.
    argument: `str`
        The argument to convert into a member object.

    Returns
    -------
    `discord.Member`
        The member object that was found from the argument.

    Raises
    ------
    `UserFeedbackException`
        If the argument could not be converted into a member object.
    """

    @staticmethod
    def get_id_match(argument: str) -> Optional[re.Match[str]]:
        """Returns a match object if the argument matches the user ID format ("<@!user_id>").

        Parameters
        ----------
        argument: `str`
            The argument to check.

        Returns
        -------
        `Optional[re.Match[str]]`
            The match object if the argument matches the user ID format, otherwise `None`.
        """

        return ID_REGEX.match(argument)

    @staticmethod
    async def query_member_named(argument: str, guild: discord.Guild) -> Optional[discord.Member]:
        """Queries the guild members by name or nickname using `guild.query_members()` and searches for a partial match.

        Parameters
        ----------
        guild: `discord.Guild`
            The guild to query the members from.
        argument: `str`
            The argument to convert into a member object.

        Returns
        -------
        `Optional[discord.Member]`
            The member object that was found from the argument.
        """

        use_cache = guild._state.member_cache_flags.joined

        if len(argument) > 5 and argument[-5] == '#':
            username, _, discriminator = argument.rpartition('#')
            members = await guild.query_members(username, limit=100, cache=use_cache)
            return discord.utils.get(members, name=username, discriminator=discriminator)

        members = await guild.query_members(argument, limit=100, cache=use_cache)
        maybe_member = discord.utils.find(lambda m: argument in (m.name, m.nick), members)
        return maybe_member or (members[0] if members else None)

    @staticmethod
    async def query_member_by_id(bot: Serenity, guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
        """Queries the guild members by ID using `guild.query_members()` and searches for an exact match.

        Parameters
        ----------
        bot: `Serenity`
            The bot instance.
        guild: `discord.Guild`
            The guild to query the members from.
        user_id: `int`
            The ID of the member to search for.

        Returns
        -------
        `Optional[discord.Member]`
            The member object that was found from the argument.
        """

        websocket = bot._get_websocket(shard_id=guild.shard_id)
        use_cache = guild._state.member_cache_flags.joined

        if websocket.is_ratelimited():
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                return None

            if use_cache:
                guild._add_member(member)

            return member

        members = await guild.query_members(limit=5, user_ids=[user_id], cache=use_cache)

        return members[0] if members else None

    @staticmethod
    def get_member_named(argument: str, guild: discord.Guild) -> Optional[discord.Member]:
        """Attempts to find a member using the guild's `get_member_named()` method.

        Parameters
        ----------
        guild: `discord.Guild`
            The guild to query the members from.
        argument: `str`
            The argument to convert into a member object.

        Returns
        -------
        `Optional[discord.Member]`
            The member object that was found from the argument.
        """

        return guild.get_member_named(argument)

    @staticmethod
    def get_member_from_guilds(bot: Serenity, getter: str, argument: str) -> Optional[discord.Member]:
        """Attempts to find a member using the `get_from_guilds()` method.

        Parameters
        ----------
        bot: `Serenity`
            The bot instance.
        method_name: `str`
            The name of the method to call on the guild object.
        argument: `str`
            The argument to convert into a member object.

        Returns
        -------
        `Optional[discord.Member]`
            The member object that was found from the argument.
        """
        for guild in bot.guilds:
            result = getattr(guild, getter)(argument)

            if result:
                return result

        return None

    @staticmethod
    def get_member_by_id(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
        """Attempts to find a member using the guild's `get_member()` method and checks the mentioned users in the message.

        Parameters
        ----------
        guild: `discord.Guild`
            The guild to query the members from.
        user_id: `int`
            The ID of the member to search for.

        Returns
        -------
        `Optional[discord.Member]`
            The member object that was found from the argument.
        """

        return guild.get_member(user_id)

    def get_member_mentioned(self, ctx: SerenityContext, user_id: int) -> Optional[discord.Member | discord.User]:
        """Attempts to find a member using the `discord.utils.get()` method.

        Parameters
        ----------
        ctx: `SerenityContext`
            The invocation context.
        user_id: `int`
            The ID of the member to search for.

        Returns
        -------
        `Optional[Union[discord.Member, discord.User]]`
            The member object that was found from the argument.
        """
        return discord.utils.get(ctx.message.mentions, id=user_id)

    @override
    async def convert(self, ctx: SerenityContext, argument: str) -> discord.Member:  # type: ignore[override]
        """Converts the argument into a `discord.Member` object.

        Parameters
        ----------
        ctx: `SerenityContext`
            The invocation context.
        argument: `str`
            The argument to convert into a member object.

        Returns
        -------
        `discord.Member`
            The member object that was found from the argument.

        Raises
        ------
        `discord.ext.commands.BadArgument`
            The argument could not be converted into a member object.
        """

        from src.shared import ExceptionFactory

        bot = ctx.bot
        guild = ctx.guild

        if guild is None:
            raise ExceptionFactory.create_warning_exception(
                f"Could not find member `{argument}` in any guild.",
            )

        result = None
        user_id = None

        match = self.get_id_match(argument) or re.match(r'<@!?([0-9]{15,20})>$', argument)

        if match is None:
            result = self.get_member_named(argument, guild) or self.get_member_from_guilds(
                bot, 'get_member_named', argument
            )
        else:
            user_id = int(match.group(1))
            result = self.get_member_by_id(guild, user_id) or self.get_member_mentioned(ctx, user_id)

        if not isinstance(result, discord.Member):
            if user_id is not None:
                result = await self.query_member_by_id(bot, guild, user_id)
            else:
                result = await self.query_member_named(argument, guild)

            if not result:
                raise ExceptionFactory.create_warning_exception(
                    f"Could not find member `{argument}` in guild `{guild.name}`.",
                )

        return result

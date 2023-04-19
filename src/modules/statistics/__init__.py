"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from utils import async_all, for_all_callbacks

from .history import TrackedDiscordHistory

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

features = (TrackedDiscordHistory,)


@for_all_callbacks(commands.cooldown(1, 3, commands.BucketType.user))
class Statistics(*features):
    """Statistics and analytics for the bot.

    Attributes
    ----------
    bot: `Bot`
        The bot instance.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    @property
    def emoji(self) -> str:
        """Get the emoji for the extension.

        Returns
        -------
        `str`
            The emoji for the extension.
        """
        return "\N{CHART WITH UPWARDS TREND}"

    async def cog_check(self, ctx: Context) -> bool:  # skipcq: PYL-R0201
        """Check that the command is being run in a guild.

        Parameters
        ----------
        ctx: `Context`
            The context of the command.

        Returns
        -------
        `bool`
            Whether the command is being run in a guild.
        """
        checks = [commands.guild_only()]
        return await async_all(check(ctx) for check in checks)


async def setup(bot: Bot) -> None:
    """Load the Statistics cog.

    Parameters
    ----------
    bot: `Bot`
        The bot instance.
    """
    await bot.add_cog(Statistics(bot))

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from utils import async_all

from .history import DiscordUserHistory

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

features = (DiscordUserHistory,)


class Statistics(*features):
    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.bot: Bot = bot

    def __repr__(self) -> str:
        return f"<Statistics Extension at {hex(id(self))}>"

    async def cog_check(self, ctx: Context) -> bool:
        checks = [commands.guild_only()]
        return await async_all(check(ctx) for check in checks)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Statistics(bot))

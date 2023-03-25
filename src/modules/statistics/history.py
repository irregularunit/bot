"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import math
import sys
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from models import EmbedBuilder
from utils import BaseExtension, CountingCalender, MemberConverter, count_source_lines
from views import AvatarHistoryView

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("DiscordUserHistory",)


class DiscordUserHistory(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    @staticmethod
    def format_count(count: int) -> str:
        return str(math.floor(count / 3))

    @commands.command(name="avatar", aliases=("av",))
    async def avatar_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(default=None, converter=MemberConverter(), displayed_default="You"),
    ) -> None:
        await AvatarHistoryView(ctx, member=member or ctx.author).start()

    @commands.command(name="info", aliases=("about",))
    async def info_command(self, ctx: Context) -> None:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        discord_version = discord.__version__
        lines_of_code = count_source_lines()

        psql_version_query = await self.bot.safe_connection.fetchval("SELECT version()")
        psql_version = psql_version_query.split(" ")[1]

        fields = (
            ("Python", python_version, True),
            ("discord.py", discord_version, True),
            ("PostgreSQL", str(psql_version), True),
            ("Lines of code", str(lines_of_code), True),
            ("Uptime", discord.utils.format_dt(self.bot.start_time, "R"), True),
            ("Latency", f"{self.bot.latency * 1000:.2f}ms", True),
        )

        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    """
                    Our bot comes equipped with a variety of features to make 
                    your server experience even better. With this valuable 
                    information at your fingertips, you'll never miss a beat when 
                    it comes to staying up-to-date with your community.

                    Whether you're a seasoned Discord user or just starting out, 
                    our bot is the perfect addition to any server.
                    """
                ),
                fields=fields,
            )
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_author(name="🔍 Servant Informationcenter")
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        await ctx.safe_send(embed=embed)

    @commands.command(name="source", aliases=("src",))
    async def source_command(self, ctx: Context) -> None:
        # The following embed pattern is a personal preference.
        # You can use any embed pattern you want. I just really
        # like this one. It feels more readable to me.
        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    """
                    Servant is an open-source bot for Discord. 
                    You can find the source code on [github](https://github.com/irregularunit/bot).

                    > Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
                    """
                )
            )
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_author(name="🔍 Servant Source Code")
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        await ctx.safe_send(embed=embed)

    @commands.command(name="score", aliases=("sc",))
    async def score_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(default=None, converter=MemberConverter(), displayed_default="You"),
    ) -> Optional[discord.Message]:
        user: discord.Member = member or ctx.author
        
        cal = CountingCalender(user.id)
        query: str = cal.struct_query()

        counting_history = await self.bot.safe_connection.fetch(query)
        embed: EmbedBuilder = (
            EmbedBuilder(
                description=f"Total score: `{self.format_count(counting_history[8]['count'])}`",
            )
            .add_field(
                name="__**Present Stats**__",
                value=(
                    f"""
                    >>> Today: `{self.format_count(counting_history[0]["count"])}`
                    This Week: `{self.format_count(counting_history[2]["count"])}`
                    This Month: `{self.format_count(counting_history[4]["count"])}`
                    This Year: `{self.format_count(counting_history[6]["count"])}`
                    """
                ),
                inline=False,
            )
            .add_field(
                name="__**Past Stats**__",
                value=(
                    f"""
                    >>> Yesterday: `{self.format_count(counting_history[1]["count"])}`
                    Last Week: `{self.format_count(counting_history[3]["count"])}`
                    Last Month: `{self.format_count(counting_history[5]["count"])}`
                    Last Year: `{self.format_count(counting_history[7]["count"])}`
                    """
                ),
                inline=False,
            )
            .set_author(name=f"{user.display_name}'s Score")
            .set_thumbnail(url=user.display_avatar)
        )

        await ctx.safe_send(embed=embed)

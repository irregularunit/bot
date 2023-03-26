"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import inspect
import math
import os
import sys
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands

from models import EmbedBuilder
from utils import (
    BaseExtension,
    CountingCalender,
    MemberConverter,
    TimeConverter,
    count_source_lines,
    get_random_emoji,
)
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

        async with self.bot.pool.acquire() as connection:
            psql_version_query = await connection.fetchval("SELECT version()")
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
                    Servant comes equipped with a variety of features to make 
                    your server experience even better. With this valuable 
                    information at your fingertips, you'll never miss a beat when 
                    it comes to staying up-to-date with your community.

                    Whether you're a seasoned Discord user or just starting out, 
                    Servant is the perfect addition to any server.
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
    async def source_command(self, ctx: Context, *, command: Optional[str] = None) -> Optional[discord.Message]:
        URL = "https://github.com/irregularunit/bot"
        LICENSE = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
        BRANCH = "development"

        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    F"""
                    Servant is an open-source bot for Discord. 
                    You can find the source code on [github]({URL}).

                    > Licensed under [CC BY-NC-SA 4.0]({LICENSE}).
                    """
                )
            )
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_author(name="🔍 Servant Source Code")
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        if command is None or command == "help":
            return await ctx.safe_send("A ⭐ is much appreciated!", embed=embed)
        else:
            cmd = self.bot.get_command(command)
            if cmd is None:
                return await ctx.safe_send("🔍 The command you are looking for does not exist.", embed=embed)

            src = getattr(cmd, "_original_callback", cmd.callback).__code__
            filename = src.co_filename

            if not filename:
                return await ctx.safe_send("🔍 The command you are looking for cannot be found.", embed=embed)

            (
                lines,
                start,
            ) = inspect.getsourcelines(src)
            end = start + len(lines) - 2
            loc = os.path.realpath(filename).replace("\\", "/").split("/bot/")[1]

            embed.add_field(
                name=f"Source Code for {cmd.name}",
                value=(
                    f"""
                    [View on Github]({URL}/blob/{BRANCH}/{loc}#L{start}-L{end})
                    """
                ),
            )

            return await ctx.safe_send(embed=embed)

    @commands.command(name="score", aliases=("sc",))
    async def score_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(default=None, converter=MemberConverter(), displayed_default="You"),
    ) -> Optional[discord.Message]:
        user: discord.Member = member or ctx.author

        cal = CountingCalender(user.id, ctx.guild.id)
        query: str = cal.struct_query()

        async with self.bot.pool.acquire() as connection:
            counting_history = await connection.fetch(query)

        def get_record_index(record: Any, idx: int) -> str:
            return self.format_count(record[idx]["count"])

        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    f"**{get_random_emoji()} {user.display_name}'s Score**\n\n"
                    f"Total score: `{get_record_index(counting_history, 8)}`"
                ),
            )
            .add_field(
                name="__**Present Stats**__",
                value=(
                    f"""
                    >>> Today: `{get_record_index(counting_history, 0)}`
                    This Week: `{get_record_index(counting_history, 2)}`
                    This Month: `{get_record_index(counting_history, 4)}`
                    This Year: `{get_record_index(counting_history, 6)}`
                    """
                ),
                inline=False,
            )
            .add_field(
                name="__**Past Stats**__",
                value=(
                    f"""
                    >>> Yesterday: `{get_record_index(counting_history, 1)}`
                    Last Week: `{get_record_index(counting_history, 3)}`
                    Last Month: `{get_record_index(counting_history, 5)}`
                    Last Year: `{get_record_index(counting_history, 7)}`
                    """
                ),
                inline=False,
            )
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        await ctx.safe_send(embed=embed)

    @commands.command(name="leaderboard", aliases=("lb",))
    async def leaderboard_command(
        self,
        ctx: Context,
        amount: int = 10,
        *,
        time: str = commands.param(default="all time", converter=TimeConverter(), displayed_default="all time"),
    ) -> Optional[discord.Message]:
        cal = CountingCalender(ctx.author.id, ctx.guild.id)
        query: str = cal.leaderboard_query(time, amount)

        async with self.bot.pool.acquire() as connection:
            leaderboard = await connection.fetch(query)

        embed: EmbedBuilder = (
            EmbedBuilder()
            .set_author(name=f"🏆 {time.title()} Leaderboard")
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        for i, row in enumerate(leaderboard, start=1):
            user = self.bot.get_user(row["uid"]) or await self.bot.fetch_user(row["uid"])
            embed.add_field(
                name=f"#{i}. {user.display_name}",
                value=f"Counting Score: `{math.floor(row['count'] / 3)}`",
                inline=False,
            )

        if not embed.fields:
            embed.description = "> No one has counted yet."

        await ctx.safe_send(embed=embed)

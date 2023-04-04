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
import time
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands
from discord.ui import Button, View, button

from models import EmbedBuilder
from utils import (
    BaseExtension,
    CountingCalender,
    MemberConverter,
    TimeConverter,
    count_source_lines,
    get_random_emoji,
)
from views import AvatarHistoryView, Item, Paginator, PluginView
from views.buttons import CollageAvatarButton, NameHistoryButton

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("DiscordUserHistory",)

BRANCH = "development"
GITHUB_URL = "https://github.com/irregularunit/bot"
LICENSE = "https://creativecommons.org/licenses/by-nc-sa/4.0/"


class InfoView(View):
    def __init__(self, invite: str, *, timeout: float = 60) -> None:
        super().__init__(timeout=timeout)
        self.inv: str = invite

        buttons = [
            Button(
                label="GitHub",
                url=GITHUB_URL,
                style=discord.ButtonStyle.link,
            ),
            Button(
                label="Invite",
                url=self.inv,
                style=discord.ButtonStyle.link,
            ),
        ]

        for button in buttons:
            self.add_item(button)

    @button(label="Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()


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

            now = time.perf_counter()
            await connection.fetchval("SELECT 1")
            psql_latency = (time.perf_counter() - now) * 1000

        fields = (
            ("Python", python_version, True),
            ("Discord.py", discord_version, True),
            ("PostgreSQL", str(psql_version), True),
            ("Lines of code", str(lines_of_code), True),
            ("PostgreSQL Latency", f"{psql_latency:.2f}ms", True),
            ("Discord Latency", f"{self.bot.latency * 1000:.2f}ms", True),
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

        view = InfoView(self.bot.config.invite)
        await ctx.safe_send(embed=embed, view=view)

    @commands.command(name="source", aliases=("src",))
    async def source_command(self, ctx: Context, *, command: Optional[str] = None) -> Optional[discord.Message]:
        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    F"""
                    Servant is an open-source bot for Discord. 
                    You can find the source code on [github]({GITHUB_URL}).

                    > Licensed under [CC BY-NC-SA 4.0]({LICENSE}).
                    """
                )
            )
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_author(name="Servant Source Code")
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        if command is None or command == "help":
            return await ctx.safe_send("A ⭐ is much appreciated!", embed=embed)
        else:
            cmd = self.bot.get_command(command)
            if cmd is None:
                return await ctx.safe_send(
                    f"{get_random_emoji()} The command you are looking for does not exist.", embed=embed
                )

            src = getattr(cmd, "_original_callback", cmd.callback).__code__
            filename = src.co_filename

            if not filename:
                return await ctx.safe_send(
                    f"{get_random_emoji()} The command you are looking for cannot be found.", embed=embed
                )

            (
                lines,
                start,
            ) = inspect.getsourcelines(src)
            end = start + len(lines) - 1
            loc = os.path.realpath(filename).replace("\\", "/").split("/bot/")[1]

            embed.add_field(
                name=f"Source Code for {cmd.name}",
                value=(
                    f"""
                    [View on Github]({GITHUB_URL}/blob/{BRANCH}/{loc}#L{start}-L{end})
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
        query = "SELECT * FROM get_counting_score($1, $2)"

        async with self.bot.pool.acquire() as connection:
            history = await connection.fetchrow(query, user.id, ctx.guild.id)

        def get_record_index(record: Any, pos: str, /) -> str:
            return self.format_count(record[pos])

        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    f"**{get_random_emoji()} {user.display_name}'s Score**\n\n"
                    f"Total score: `{get_record_index(history, 'all_time')}`"
                ),
            )
            .add_field(
                name="__**Present Stats**__",
                value=(
                    f"""
                    >>> Today: `{get_record_index(history, 'today')}`
                    This Week: `{get_record_index(history, 'this_week')}`
                    This Month: `{get_record_index(history, 'this_month')}`
                    This Year: `{get_record_index(history, 'this_year')}`
                    """
                ),
                inline=False,
            )
            .add_field(
                name="__**Past Stats**__",
                value=(
                    f"""
                    >>> Yesterday: `{get_record_index(history, 'yesterday')}`
                    Last Week: `{get_record_index(history, 'last_week')}`
                    Last Month: `{get_record_index(history, 'last_month')}`
                    Last Year: `{get_record_index(history, 'last_year')}`
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
        amount: Optional[int] = 10,
        *,
        time: str = commands.param(default="all time", converter=TimeConverter(), displayed_default="all time"),
    ) -> Optional[discord.Message]:
        cal = CountingCalender(ctx.author.id, ctx.guild.id)
        query: str = cal.leaderboard_query(time, amount if amount else 10)

        async with self.bot.pool.acquire() as connection:
            leaderboard = await connection.fetch(query)

        embed: EmbedBuilder = (
            EmbedBuilder()
            .set_author(name=f"🏆 {time.title()} Leaderboard")
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        for i, row in enumerate(leaderboard, start=1):
            user_id = row["uuid"]
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)

            embed.add_field(
                name=f"#{i}. {user.display_name}",
                value=f"Counting Score: `{math.floor(row['count'] / 3)}`",
                inline=False,
            )

        if not embed.fields:
            embed.description = "> No one has counted yet."

        await ctx.safe_send(embed=embed)

    @commands.command(name="userinfo", aliases=("ui",))
    async def userinfo_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(default=None, converter=MemberConverter(), displayed_default="You"),
    ) -> Optional[discord.Message]:
        user: discord.Member = member or ctx.author
        joined_at = user.joined_at or discord.utils.utcnow()

        view = PluginView(ctx, member=user)
        view.add_item(
            NameHistoryButton(
                label="Username History",
                style=discord.ButtonStyle.blurple,
                emoji="📜",
            )
        )
        view.add_item(
            CollageAvatarButton(
                label="Avatar Collage",
                style=discord.ButtonStyle.blurple,
                emoji="🖼️",
            )
        )

        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    f"""
                    **{get_random_emoji()} {user.display_name}'s Info**\n
                    **User ID:** `{user.id}`
                    **Account Created:** `{user.created_at.strftime("%b %d, %Y")}`
                    **Joined Server:** `{joined_at.strftime("%b %d, %Y")}`
                    """
                )
            )
            .set_thumbnail(url=user.display_avatar)
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
        )

        await ctx.safe_send(embed=embed, view=view)

    @commands.command(name="joinlist", aliases=("jl",))
    async def joinlist_command(self, ctx: Context) -> Optional[discord.Message]:
        sorted_list = sorted(ctx.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow())

        pages: list[str] = [
            "\n".join(
                f"**{i + 1}.** {member.display_name} - {discord.utils.format_dt(member.joined_at or discord.utils.utcnow(), style='R')}"
                for i, member in enumerate(sorted_list[page * 10 : (page + 1) * 10])
            )
            for page in range(math.ceil(len(sorted_list) / 10))
        ]
        items: list[Item] = [
            Item(
                embed=EmbedBuilder(
                    description=page,
                    color=discord.Color.blurple(),
                )
                .set_footer(text=f"Page {i + 1} of {len(pages)}")
                .set_author(name=f"📜 Join List")
                .set_thumbnail(url=self.bot.user.display_avatar)
                .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
            )
            for i, page in enumerate(pages)
        ]

        view = Paginator(self.bot, *items)
        await ctx.safe_send(view=view, embed=items[0].embed)

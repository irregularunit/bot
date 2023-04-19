"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import datetime
import inspect
import math
import sys
import time as _time
from collections import defaultdict
from os import path
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands
from discord.ui import Button, View, button
from pympler.asizeof import asizeof

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory
from models import EmbedBuilder
from pil import PresenceChart, PresenceType
from utils import (
    BaseExtension,
    CountingCalender,
    MemberConverter,
    TimeConverter,
    Timer,
    count_source_lines,
    get_random_emoji,
)
from views import AvatarHistoryView, Item, Paginator, PluginView
from views.buttons import CollageAvatarButton, NameHistoryButton

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("TrackedDiscordHistory",)

BRANCH = "development"
GITHUB_URL = "https://github.com/irregularunit/bot"
LICENSE = "https://creativecommons.org/licenses/by-nc-sa/4.0/"


class InfoView(View):
    """A view to display information about the bot.

    Attributes
    ----------
    inv: `str`
        The invite link for the bot.
    what: `str`
        What ever link to set as the button.
    timeout: `float`
        The timeout for the view.
    """

    def __init__(self, inv: str, what: str, *, timeout: float = 60) -> None:
        super().__init__(timeout=timeout)
        self.inv: str = inv
        self.what: str = what

        buttons: list[Button["InfoView"]] = [
            Button(
                label="GitHub",
                url=GITHUB_URL,
                style=discord.ButtonStyle.link,
            ),
            Button(
                label=self.what,
                url=self.inv,
                style=discord.ButtonStyle.link,
            ),
        ]

        for item in buttons:
            self.add_item(item)

    @button(label="Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, btn: Button["InfoView"]) -> None:
        """Close the view."""
        await interaction.response.defer()
        await interaction.delete_original_response()


class TrackedDiscordHistory(BaseExtension):
    """A class to track discord history."""

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    @staticmethod
    def format_count(count: int) -> str:
        """Format a count to a string.

        Parameters
        ----------
        count: `int`
            The count to format.

        Returns
        -------
        `str`
            The formatted count.
        """
        return str(math.floor(count / 3))

    @commands.command(name="avatar", aliases=("av",))
    async def avatar_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(
            default=None, converter=MemberConverter(), displayed_default="You"
        ),
    ) -> None:
        await AvatarHistoryView(ctx, member=member or ctx.referenced_user or ctx.author).start()

    @commands.command(name="info", aliases=("about",))
    async def info_command(self, ctx: Context) -> None:
        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        discord_version = discord.__version__
        lines_of_code = count_source_lines()

        async with self.bot.pool.acquire() as connection:
            psql_version_query = await connection.fetchval("SELECT version()")
            psql_version = psql_version_query.split(" ")[1]

            now = _time.perf_counter()
            await connection.fetchval("SELECT 1")
            psql_latency = (_time.perf_counter() - now) * 1000

        fields = (
            ("Python", python_version, True),
            ("Discord.py", discord_version, True),
            ("Lines of code", str(lines_of_code), True),
            ("PostgreSQL", str(psql_version), True),
            ("PostgreSQL Latency", f"{psql_latency:.2f}ms", True),
            ("Discord Latency", f"{self.bot.latency * 1000:.2f}ms", True),
        )

        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    f"""
                    {self.bot.user.name} comes equipped with a variety of features to make 
                    your server experience even better. With this valuable 
                    information at your fingertips, you'll never miss a beat when 
                    it comes to staying up-to-date with your community.

                    Whether you're a seasoned Discord user or just starting out, 
                    {self.bot.user.name} is the perfect addition to any server.
                    """
                ),
                fields=fields,
            )
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_author(name=f"🔍 {self.bot.user.name} Informationcenter")
            .set_footer(
                text="Made with ❤️ by irregularunit.",
                icon_url=self.bot.user.display_avatar,
            )
        )

        view = InfoView(self.bot.config.invite, "Invite")
        await ctx.safe_send(embed=embed, view=view)

    @commands.command(name="source", aliases=("src",))
    async def source_command(
        self, ctx: Context, *, command: Optional[str] = None
    ) -> Optional[discord.Message]:
        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    f"""
                    {self.bot.user.name} is an open-source discord bot. 
                    Feel free to contribute to the project.

                    > ⭐ Star this repository on [GitHub]({GITHUB_URL}) to show your support.
                    > 🐛 Report bugs or request features on [Issues]({GITHUB_URL}/issues).
                    > 📖 Read the documentation on [Docs]({GITHUB_URL}/tree/{BRANCH}/docs).
                    > 📝 Contribute to the source code on [Base]({GITHUB_URL}/tree/{BRANCH}).
                    > 📚 Learn more about the bot on [About]({GITHUB_URL}/blob/{BRANCH}/README.md).
                    """
                )
            )
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_author(name=f"{self.bot.user.name} Source Code")
            .set_footer(
                text="Made with ❤️ by irregularunit.",
                icon_url=self.bot.user.display_avatar,
            )
        )

        if command is None or command == "help":
            return await ctx.safe_send("A ⭐ is much appreciated!", embed=embed)

        cmd = self.bot.get_command(command)
        if cmd is None:
            return await ctx.safe_send(
                f"{get_random_emoji()} The command you are looking for does not exist.",
                embed=embed,
            )

        src = getattr(cmd, "_original_callback", cmd.callback).__code__
        filename = src.co_filename

        if not filename:
            return await ctx.safe_send(
                f"{get_random_emoji()} The command you are looking for cannot be found.",
                embed=embed,
            )

        (
            lines,
            start,
        ) = inspect.getsourcelines(src)
        end = start + len(lines) - 1
        loc = path.realpath(filename).replace("\\", "/").split("/bot/")[1]
        view = InfoView(
            f"{GITHUB_URL}/blob/{BRANCH}/{loc}#L{start}-L{end}",
            f"{cmd.name.title()}",
        )

        return await ctx.safe_send(embed=embed, view=view)

    @commands.command(name="score", aliases=("sc",))
    async def score_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(
            default=None, converter=MemberConverter(), displayed_default="You"
        ),
    ) -> Optional[discord.Message]:
        user: discord.Member = member or ctx.referenced_user or ctx.author
        query = "SELECT * FROM get_counting_score($1, $2)"

        async with self.bot.pool.acquire() as connection:
            history = await connection.fetchrow(query, user.id, ctx.guild.id)

        def get_record_index(record: Any, pos: str, /) -> str:
            """Get the record index from the database.

            Parameters
            ----------
            record : `Any`
                The record to get the index from.
            pos : `str`
                The position of the index to get.

            Returns
            -------
            `str`
                The index from the record.
            """
            return self.format_count(record[pos])

        embed: EmbedBuilder = (
            EmbedBuilder(
                description=(
                    f"**{get_random_emoji()} {user.display_name}'s Statistics**\n\n"
                    f"Total: `{get_record_index(history, 'all_time')}`"
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
            .set_footer(
                text="Made with ❤️ by irregularunit.",
                icon_url=self.bot.user.display_avatar,
            )
        )

        await ctx.safe_send(embed=embed)

    @commands.command(name="leaderboard", aliases=("lb",))
    async def leaderboard_command(
        self,
        ctx: Context,
        amount: Optional[int] = 10,
        *,
        time: str = commands.param(
            default="all time",
            converter=TimeConverter(),
            displayed_default="all time",
        ),
    ) -> Optional[discord.Message]:
        cal = CountingCalender(ctx.author.id, ctx.guild.id)
        query: str = cal.leaderboard_query(time, amount if amount else 10)

        async with self.bot.pool.acquire() as connection:
            leaderboard = await connection.fetch(query)

        embed: EmbedBuilder = (
            EmbedBuilder()
            .set_author(name=f"🏆 {time.title()} Leaderboard")
            .set_thumbnail(url=self.bot.user.display_avatar)
            .set_footer(
                text="Made with ❤️ by irregularunit.",
                icon_url=self.bot.user.display_avatar,
            )
        )

        for i, row in enumerate(leaderboard, start=1):
            user_id = row["uuid"]
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)

            embed.add_field(
                name=f"#{i}. {user.display_name}",
                value=f"Count: `{math.floor(row['count'] / 3)}`",
                inline=False,
            )

        if not embed.fields:
            embed.description = "> No one counter entries yet."

        await ctx.safe_send(embed=embed)

    @commands.command(name="userinfo", aliases=("ui",))
    async def userinfo_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(
            default=None, converter=MemberConverter(), displayed_default="You"
        ),
    ) -> Optional[discord.Message]:
        user: discord.Member = member or ctx.referenced_user or ctx.author
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
            .set_footer(
                text="Made with ❤️ by irregularunit.",
                icon_url=self.bot.user.display_avatar,
            )
        )

        await ctx.safe_send(embed=embed, view=view)

    @commands.command(name="joinlist", aliases=("jl",))
    async def joinlist_command(self, ctx: Context) -> Optional[discord.Message]:
        sorted_list: list[discord.Member] = sorted(
            ctx.guild.members,
            key=lambda m: m.joined_at or discord.utils.utcnow(),
        )

        items: list[Item] = [
            Item(
                embed=EmbedBuilder(
                    description="\n".join(
                        f"**{i + 1}.** {member.display_name} - "
                        f"{discord.utils.format_dt(member.joined_at or discord.utils.utcnow(), style='R')}"
                        for i, member in enumerate(sorted_list[page * 10 : (page + 1) * 10])
                    ),
                    color=discord.Color.blurple(),
                )
                .set_footer(text=f"Page {i + 1} of {math.ceil(len(sorted_list) / 10)}")
                .set_author(name=f"📜 Join List for {ctx.guild.name}")
                .set_thumbnail(url=self.bot.user.display_avatar)
                .set_footer(
                    text="Made with ❤️ by irregularunit.",
                    icon_url=self.bot.user.display_avatar,
                )
            )
            for i, page in enumerate(range(math.ceil(len(sorted_list) / 10)))
        ]

        view = Paginator(self.bot, *items)
        await ctx.safe_send(view=view, embed=items[0].embed)

    async def get_presence_history(self, user_id: int, query_days: int) -> list[Record]:
        async with self.bot.pool.acquire() as connection:
            return await connection.fetch(
                """
                SELECT status, status_before, changed_at FROM presence_history
                WHERE uuid = $1 AND changed_at >= $2 ORDER BY changed_at DESC
                """,
                user_id,
                datetime.datetime.utcnow() - datetime.timedelta(days=query_days),
            )

    @commands.command(name="presence", aliases=("ps",))
    async def presence_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(
            default=None, converter=MemberConverter(), displayed_default="You"
        ),
    ) -> Optional[discord.Message]:
        query_days: int = 1
        user: discord.Member = member or ctx.referenced_user or ctx.author

        with Timer() as timer:
            history: list[Record] = await self.get_presence_history(user.id, query_days)
            query_time = timer.elapsed
            timer.reset()

            if not history:
                raise UserFeedbackExceptionFactory.create(
                    "No presence history found for this user.",
                    level=ExceptionLevel.INFO,
                )

            record_dict = {
                record["changed_at"]: [
                    record["status"],
                    record["status_before"],
                ]
                for record in history
            }

            status_time: defaultdict[str, float] = defaultdict(float)
            sorted_presences = sorted(record_dict.items())

            for i in range(len(sorted_presences) - 1):
                curr_datetime, curr_status = sorted_presences[i]
                next_datetime, next_status = sorted_presences[i + 1]
                curr_status = curr_status[1]  # old status
                next_status = next_status[0]  # new status
                time_diff = (next_datetime - curr_datetime).total_seconds()

                if curr_status == next_status:
                    status_time[curr_status] += time_diff
                else:
                    status_time[curr_status] += (60 * 60 * 24 - curr_datetime.second) - sum(
                        status_time.values()
                    )
                    status_time[next_status] += time_diff

            try:
                status_time[sorted_presences[0][1][1]] += 86_401 - sum(status_time.values())
            except KeyError:
                # Didn't wanna use get, here so that's why this is here
                status_time[sorted_presences[0][1][1]] = 86_401 - sum(status_time.values())

            analysis_time = timer.elapsed
            timer.reset()

            presence_data = PresenceType(
                avatar=await user.display_avatar.read(),
                labels=["idle", "online", "dnd", "offline"],
                colors=["#fba31c", "#43b581", "#f04747", "#747f8d"],
                values=[
                    int(status_time.get("Idle", 0)),
                    int(status_time.get("Online", 0)),
                    int(status_time.get("Do Not Disturb", 0)),
                    int(status_time.get("Offline", 0)),
                ],
            )

            presence_instance = PresenceChart(presence_data)
            canvas: discord.File = await self.bot.to_thread(presence_instance.create)

            await ctx.maybe_reply(
                content=(
                    f"Presence pie chart for {user.display_name} since "
                    f"{(datetime.datetime.utcnow() - datetime.timedelta(days=query_days)).strftime('%b %d, %Y')}\n"
                    f"`Query time:    ` `{query_time:.2f}s`\n"
                    f"`Analysis time: ` `{analysis_time:.2f}s`\n"
                    f"`Canvas time:   ` `{timer.stop():.2f}s`"
                ),
                file=canvas,
            )

    @commands.command(name="lastseen", aliases=("ls",))
    async def lastseen_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(
            default=None, converter=MemberConverter(), displayed_default="You"
        ),
    ) -> Optional[discord.Message]:
        user: discord.Member = member or ctx.referenced_user or ctx.author

        with Timer() as timer:
            history: list[Record] = await self.get_presence_history(user.id, 100)
            query_time = timer.elapsed
            timer.reset()

            if not history:
                raise UserFeedbackExceptionFactory.create(
                    "No presence history found for this user.",
                    level=ExceptionLevel.INFO,
                )

            last_seen: datetime.datetime = history[0]["changed_at"]
            last_seen_status: str = history[0]["status_before"]

            await ctx.maybe_reply(
                content=(
                    f"**{user.display_name}** was last seen "
                    f"{discord.utils.format_dt(last_seen, style='R')} "
                    f"({discord.utils.format_dt(last_seen, style='F')}) "
                    f"with status **{last_seen_status}**.\nWith a query time of "
                    f"`{query_time:.2f}s` and an analysis time of `{timer.stop():.2f}s`."
                )
            )

    @commands.command(name="botstats", aliases=("bs",))
    async def botstats_command(self, ctx: Context) -> Optional[discord.Message]:
        async with self.bot.pool.acquire() as connection:
            with Timer() as timer:
                bot_stats = await connection.fetchrow(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM presence_history) AS presence_count,
                        (SELECT COUNT(*) FROM guilds) AS guild_count,
                        (SELECT COUNT(*) FROM users) AS user_count,
                        (SELECT COUNT(*) FROM avatar_history) AS avatar_count,
                        (SELECT COUNT(*) FROM item_history) AS item_count
                    """
                )
                query_time = timer.stop()

            if not bot_stats:
                raise UserFeedbackExceptionFactory.create(
                    "No bot stats found.",
                    level=ExceptionLevel.INFO,
                )

            bot_memory = asizeof(self.bot)
            cached_users_memory = asizeof(self.bot.cached_users)
            cached_guilds_memory = asizeof(self.bot.cached_guilds)

            await ctx.maybe_reply(
                content=(
                    "```"
                    f"Users:                    {bot_stats['user_count']}\n"
                    f"Guilds:                   {bot_stats['guild_count']}\n"
                    f"Presence history entries: {bot_stats['presence_count']}\n"
                    f"Avatar history entries:   {bot_stats['avatar_count']}\n"
                    f"Item history entries:     {bot_stats['item_count']}\n"
                    f"Bot memory:               {bot_memory} bytes\n"
                    f"Release version:          {self.bot.version}\n"
                    f"Bound license:            {self.bot.license}\n"
                    f"Creator Link:             {self.bot.author}\n"
                    f"Cached users memory:      {cached_users_memory} bytes\n"
                    f"Cached guilds memory:     {cached_guilds_memory} bytes\n"
                    f"Query time:               {query_time:.2f}s"
                    "```"
                )
            )

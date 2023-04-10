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
import time
from io import BytesIO
from math import ceil, cos, radians, sin
from os import path
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands
from discord.ui import Button, View, button
from PIL import Image, ImageDraw, ImageFont

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory
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

__all__: tuple[str, ...] = ("TrackedDiscordHistory",)

BRANCH = "development"
GITHUB_URL = "https://github.com/irregularunit/bot"
LICENSE = "https://creativecommons.org/licenses/by-nc-sa/4.0/"


class InfoView(View):
    def __init__(self, inv: str, what: str, *, timeout: float = 60) -> None:
        super().__init__(timeout=timeout)
        self.inv: str = inv
        self.what: str = what

        buttons = [
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
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()


class TrackedDiscordHistory(BaseExtension):
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
        member: discord.Member = commands.param(
            default=None, converter=MemberConverter(), displayed_default="You"
        ),
    ) -> None:
        await AvatarHistoryView(
            ctx, member=member or ctx.referenced_user or ctx.author
        ).start()

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
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(
                user_id
            )

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
    async def joinlist_command(
        self, ctx: Context
    ) -> Optional[discord.Message]:
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
                        for i, member in enumerate(
                            sorted_list[page * 10 : (page + 1) * 10]
                        )
                    ),
                    color=discord.Color.blurple(),
                )
                .set_footer(
                    text=f"Page {i + 1} of {math.ceil(len(sorted_list) / 10)}"
                )
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

    @commands.command(name="presence", aliases=("ps",))
    async def presence_command(
        self,
        ctx: Context,
        days: Optional[int] = 1,
        *,
        member: discord.Member = commands.param(
            default=None, converter=MemberConverter(), displayed_default="You"
        ),
    ) -> Optional[discord.Message]:
        query_days = min(days if days else 1, 30)
        user: discord.Member = member or ctx.referenced_user or ctx.author

        async with self.bot.pool.acquire() as connection:
            history = await connection.fetch(
                """
                SELECT status, status_before, changed_at FROM presence_history
                WHERE uuid = $1 AND changed_at >= $2 ORDER BY changed_at DESC
                """,
                user.id,
                datetime.datetime.utcnow()
                - datetime.timedelta(days=query_days),
            )

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

            status_time: dict[str, float] = {}
            sorted_presences = sorted(record_dict.items())

            for i in range(len(sorted_presences) - 1):
                curr_datetime, curr_status = sorted_presences[i]
                next_datetime, next_status = sorted_presences[i + 1]
                curr_status = curr_status[1]  # old status
                next_status = next_status[0]  # new status
                time_diff = (next_datetime - curr_datetime).total_seconds()

                if curr_status == next_status:
                    if curr_status in status_time:
                        status_time[curr_status] += time_diff
                    else:
                        status_time[curr_status] = time_diff
                else:
                    if next_status in status_time:
                        status_time[next_status] += time_diff
                    else:
                        status_time[next_status] = time_diff

            status_time[sorted_presences[0][1][1]] += 86_400 - sum(
                status_time.values()
            )

            canvas: discord.File = await self.bot.to_thread(
                self.create_presence_pie,
                await user.display_avatar.read(),
                status_time,
            )
            await ctx.maybe_reply(
                content=f"Presence pie chart for {user.display_name} since "
                f"{(datetime.datetime.utcnow() - datetime.timedelta(days=query_days)).strftime('%b %d, %Y')}",
                file=canvas,
            )

    @staticmethod
    def create_presence_pie(
        user: bytes, status_time: dict[str, float]
    ) -> discord.File:
        total = 86_400
        stat_degrees = {k: (v / total) * 360 for k, v in status_time.items()}

        angles = {}
        starting = -90

        for k, v in stat_degrees.items():
            angles[k] = starting + v
            starting += v

        base_layer = Image.new("RGBA", size=(400, 300), color=(0, 0, 0, 0))
        pie_layer = Image.new("RGBA", size=(400, 300), color=(0, 0, 0, 0))

        status = {
            'Online': (59, 165, 93),
            'Idle': (250, 168, 26),
            'Do Not Disturb': (237, 66, 69),
            'Offline': (116, 127, 141),
        }
        neutral = (188, 188, 188)

        with Image.open(BytesIO(user)).resize(
            (200, 200), resample=Image.BICUBIC
        ).convert('RGBA') as canvas:
            with Image.open("static/images/piechart.png").convert("L") as mask:
                base_layer.paste(canvas, (50, 50), canvas)

                basepen = ImageDraw.Draw(pie_layer)

                for k, v in angles.items():
                    if starting == v:
                        continue

                    basepen.pieslice(
                        ((-5, -5), (305, 305)), starting, v, fill=status[k]
                    )
                    starting = v

                if 360 not in stat_degrees:
                    mult = 1000
                    offset = 150
                    for k, v in angles.items():
                        x = (
                            offset
                            + ceil(offset * mult * cos(radians(v))) / mult
                        )
                        y = (
                            offset
                            + ceil(offset * mult * sin(radians(v))) / mult
                        )
                        basepen.line(
                            ((offset, offset), (x, y)),
                            fill=(255, 255, 255, 255),
                            width=1,
                        )

                del basepen
                pie_layer.putalpha(mask)

        font = ImageFont.truetype("static/fonts/Arial.ttf", 14)
        by = {'Online': 60, 'Idle': 110, 'Do Not Disturb': 160, 'Offline': 210}

        base_layer.paste(pie_layer, None, pie_layer)
        basepen = ImageDraw.Draw(base_layer)

        for k, v in status_time.items():
            basepen.rectangle(
                ((310, by[k]), (310 + 30, by[k] + 30)),
                fill=status[k],
                outline=(255, 255, 255, 255),
            )
            basepen.text(
                (310 + 40, by[k] + 8),
                f'{(v/total)*100:.2f}%',
                fill=neutral,
                font=font,
            )

        del basepen

        # enhance the image quality
        base_layer = base_layer.resize(
            (base_layer.width * 2, base_layer.height * 2),
            resample=Image.BICUBIC,
        )

        buffer = BytesIO()
        base_layer.save(buffer, format="PNG")
        buffer.seek(0)

        return discord.File(buffer, filename="presence.png")

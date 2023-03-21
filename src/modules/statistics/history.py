from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from models import EmbedBuilder
from views import AvatarHistoryView
from utils import BaseExtension, MemberConverter, count_source_lines

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("DiscordUserHistory",)


class DiscordUserHistory(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.bot: Bot = bot

    @commands.command(name="avatar", aliases=("av",))
    async def avatar_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(default=None, converter=MemberConverter(), displayed_default="You"),
    ) -> None:
        await AvatarHistoryView(ctx, member=member or ctx.author).start()

    @commands.command(name="info", aliases=("about",))
    async def source_command(self, ctx: Context) -> None:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        discord_version = discord.__version__
        lines_of_code = count_source_lines()

        psql_version_query = await self.bot.safe_connection.fetchval("SELECT version()")
        psql_version = psql_version_query.split(" ")[1]

        fields = (
            ("Python", python_version, True),
            ("discord.py", discord_version, True),
            ("PostgreSQL", psql_version, True),
            ("Lines of code", lines_of_code, True),
            ("Uptime", discord.utils.format_dt(self.bot.start_time, "R"), True),
            ("Latency", f"{self.bot.latency * 1000:.2f}ms", True),
        )
        
        embed: EmbedBuilder = (
            EmbedBuilder(
                description=self.bot.description,
                fields=fields,  # type: ignore
                timestamp=self.bot.start_time,
            )
            .set_author(name="About Storybook", icon_url=self.bot.user.display_avatar)
            .set_footer(text="Made with ❤️ by irregularunit.")
        )

        await ctx.maybe_reply(embed=embed)

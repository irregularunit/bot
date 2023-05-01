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

from __future__ import annotations

from sys import version_info
from time import perf_counter
from typing import TYPE_CHECKING, TypeVar

import discord
from discord.ext import commands
from discord.utils import async_all
from typing_extensions import override

from src.shared import Plugin, SerenityEmbed

from .utils import count_source_lines
from .views import AboutSerenityView

if TYPE_CHECKING:
    from src.models.serenity import Serenity
    from src.models.discord import SerenityContext


__all__: tuple[str, ...] = ("Meta",)

BotT = TypeVar("BotT", bound="commands.Bot")


class Meta(Plugin):
    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity

    @override
    async def cog_check(self, ctx: SerenityContext) -> bool:
        checks = (commands.guild_only(),)
        return await async_all(check(ctx) for check in checks) and await super().cog_check(ctx)

    @commands.command(
        name="info",
        aliases=(
            "about",
            "botinfo",
        ),
        help="Shows information about Serenity.",
    )
    async def info_command(self, ctx: SerenityContext) -> None:
        python_version = (
            f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        )
        discord_version = discord.__version__
        lines_of_code = count_source_lines()

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                now = perf_counter()
                psql_version = await conn.fetchval("SELECT version()")
                psql_version = psql_version.split()[1:2]
                psql_version = "".join(psql_version)
                latency = (perf_counter() - now) * 1000

        fields = (
            ("Python", python_version, True),
            ("Discord.py", discord_version, True),
            ("Lines of code", str(lines_of_code), True),
            ("PostgreSQL", str(psql_version), True),
            ("PostgreSQL Latency", f"{latency:.2f}ms", True),
            ("Discord Latency", f"{self.serenity.latency * 1000:.2f}ms", True),
        )

        embed = (
            SerenityEmbed.factory(
                ctx,
                description=(
                    f"""
                    {ctx.me.name} comes equipped with a variety of features to make 
                    your server experience even better. With this valuable 
                    information at your fingertips, you'll never miss a beat when 
                    it comes to staying up-to-date with your community.

                    Whether you're a seasoned Discord user or just starting out, 
                    {ctx.me.name} is the perfect addition to any server.
                    """
                ),
                fields=fields,
            )
            .set_thumbnail(url=ctx.me.display_avatar.url)
            .set_author(name=f"{ctx.me.display_name} Information", icon_url=ctx.me.display_avatar.url)
        )

        await ctx.send(
            embed=embed,
            view=AboutSerenityView(ctx.author.id, self.serenity.config.invite, "Invite"),
        )

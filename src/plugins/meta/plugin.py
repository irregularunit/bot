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
from typing import TYPE_CHECKING, Optional, Tuple

import discord
from discord.ext import commands
from typing_extensions import override

from src.shared import MaybeMemberParam, Plugin, SerenityEmbed, Stopwatch, for_command_callbacks

from .extras import avatar_info_extra, bot_info_extra, source_code_extra
from .utils import GITHUB_URL, count_source_lines, get_source_information
from .views import AboutSerenityView

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity

__all__: Tuple[str, ...] = ("Meta",)


@for_command_callbacks(commands.cooldown(1, 5, commands.BucketType.user))
class Meta(Plugin):
    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity

    @commands.command(name="about", aliases=("info", "botinfo", "bot"), extras=bot_info_extra)
    async def about(self, ctx: SerenityContext) -> None:
        me = ctx.me
        python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        discord_version = discord.__version__
        lines_of_code = await self.serenity.to_thread(count_source_lines)

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                with Stopwatch() as sw:
                    psql_version = await conn.fetchval("SELECT version();")
                    psql_latency = sw.elapsed

                psql_version = psql_version.split()[1:2]
                psql_version = "".join(psql_version)

        fields: Tuple[Tuple[str, str, bool], ...] = (
            ("Python", python_version, True),
            ("Discord.py", discord_version, True),
            ("Lines of code", str(lines_of_code), True),
            ("PostgreSQL", str(psql_version), True),
            ("PostgreSQL Latency", f"{psql_latency:.2f}ms", True),
            ("Discord Latency", f"{self.serenity.latency * 1000:.2f}ms", True),
        )

        embed = (
            SerenityEmbed.factory(
                ctx,
                description=(
                    f"""
                    {me.name} comes equipped with a variety of features to make 
                    your server experience even better. With this valuable 
                    information at your fingertips, you'll never miss a beat when 
                    it comes to staying up-to-date with your community.

                    Whether you're a seasoned Discord user or just starting out, 
                    {me.name} is the perfect addition to any server.
                    """
                ),
                fields=fields,
            )
            .set_thumbnail(url=me.display_avatar.url)
            .set_author(
                name=f"{me.display_name} Information",
                icon_url=me.display_avatar.url,
            )
        )

        await ctx.maybe_reply(
            embed=embed,
            view=AboutSerenityView(ctx.author.id, self.serenity.config.invite, "Invite"),
        )

    @commands.command(name="avatar", aliases=("av", "pfp"), extras=avatar_info_extra)
    async def avatar(self, ctx: SerenityContext, *, member: discord.User = MaybeMemberParam) -> None:
        user = member or ctx.author

        webp = user.display_avatar.with_format("webp").url
        png = user.display_avatar.with_format("png").url
        jpg = user.display_avatar.with_format("jpg").url
        gif = user.display_avatar.url if user.display_avatar.is_animated() else None

        embed = SerenityEmbed(
            description=(f"[webp]({webp}) | [png]({png}) | [jpg]({jpg}) {'| [gif]({})'.format(gif) if gif else ''}")
        )
        embed.set_author(name=f"{user.display_name}'s avatar", icon_url=user.display_avatar)
        embed.set_image(url=user.display_avatar.url)

        await ctx.maybe_reply(embed=embed)

    @commands.command(name="source", aliases=("src", "code"), extras=source_code_extra)
    async def source(self, ctx: SerenityContext, *, command: str = "") -> Optional[discord.Message]:
        if not command or command == 'help':
            return await ctx.maybe_reply(GITHUB_URL)

        obj = self.serenity.get_command(command.replace('.', ' '))
        if obj is None:
            return await ctx.maybe_reply(f"Command `{command}` not found.")

        src = await self.serenity.to_thread(get_source_information, obj)

        embed = SerenityEmbed.factory(
            ctx,
            description=(
                f"""
                    __**Source on [Github]({src.url})**__
                    >>> {src.notes}
                    **Module:** `{src.module.split("src.plugins.")[-1]}`
                    **Lines:** `{src.lines}`
                    """
            ),
        )

        return await ctx.maybe_reply(embed=embed)

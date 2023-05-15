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
from typing import TYPE_CHECKING, Tuple

import discord
from discord.ext import commands
from typing_extensions import override

from src.shared import MaybeMemberParam, Plugin, SerenityEmbed, Stopwatch, for_command_callbacks, ExceptionFactory

from .extras import avatar_info_extra, bot_info_extra, git_history_extra
from .utils import count_source_lines, get_git_history
from .views import AboutSerenityView

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity

__all__: Tuple[str, ...] = ("Meta",)


@for_command_callbacks(commands.cooldown(1, 5, commands.BucketType.user))
class Meta(Plugin):
    """A plugin that provides information about the bot."""

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

    @commands.command(name="githistory", aliases=("gh",), extras=git_history_extra)
    async def githistory(self, ctx: SerenityContext) -> None:
        try:
            history = await self.serenity.to_thread(get_git_history)
        except OSError:
            raise ExceptionFactory.create_info_exception(
                "Failed to retrieve git history. Please try again later."
            ) from None

        await ctx.safe_send(content=f"```yaml\n{history}\n```")

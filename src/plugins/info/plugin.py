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

from uuid import uuid4
from sys import version_info
from time import perf_counter
from typing import TYPE_CHECKING, Union

import discord
from discord.ext import commands
from discord.utils import async_all
from typing_extensions import override

from src.models.discord.converter import MaybeMember
from src.shared import (
    AvatarCollage,
    ExceptionFactory,
    FilePointer,
    Plugin,
    SerenityEmbed,
    Stopwatch,
)

from .utils import count_source_lines
from .views import AboutSerenityView

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Info",)


class Info(Plugin):
    """The Info plugin provides information about Discord and Serenity."""

    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity

    @override
    async def cog_check(self, ctx: SerenityContext) -> bool:
        checks = (commands.guild_only(),)
        return await async_all(
            check(ctx) for check in checks
        ) and await super().cog_check(ctx)

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
        lines_of_code = await self.serenity.to_thread(count_source_lines)

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
            .set_author(
                name=f"{ctx.me.display_name} Information",
                icon_url=ctx.me.display_avatar.url,
            )
        )

        await ctx.send(
            embed=embed,
            view=AboutSerenityView(
                ctx.author.id, self.serenity.config.invite, "Invite"
            ),
        )

    @commands.command(
        name="avatar",
        aliases=("av",),
        help="Shows the avatar of a user.",
    )
    async def avatar_command(
        self,
        ctx: SerenityContext,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author

        webp = user.display_avatar.with_format("webp").url
        png = user.display_avatar.with_format("png").url
        jpg = user.display_avatar.with_format("jpg").url
        gif = user.display_avatar.url if user.display_avatar.is_animated() else None

        embed = (
            SerenityEmbed(
                description=(
                    f"[webp]({webp}) | [png]({png}) | [jpg]({jpg}) {'| [gif]({})'.format(gif) if gif else ''}"
                )
            )
            .set_author(
                name=f"{user.display_name}'s avatar", icon_url=user.display_avatar
            )
            .set_image(url=user.display_avatar.url)
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="avatarhistory",
        aliases=("avhy", "avh"),
        help="Shows the avatar history of a user.",
    )
    async def avatar_history_command(
        self,
        ctx: SerenityContext,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author
        pointer = FilePointer(user.id)

        if pointer.empty:
            raise ExceptionFactory.create_warning_exception(
                f"{user.display_name} has no avatar history."
            )

        with Stopwatch() as timer:
            collage = await AvatarCollage(pointer).buffer()
            elapsed = timer.elapsed

        file = discord.File(collage, filename=f"{uuid4()}.png")

        embed = (
            SerenityEmbed(
                description=(
                    f"> Generating took `{elapsed:.2f}` seconds.\n"
                    f"> Showing `{len(pointer)}` of up to `100` changes."
                )
            )
            .set_author(
                name=f"{user.display_name}'s avatar history",
                icon_url=user.display_avatar,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        await ctx.send(embed=embed, file=file)

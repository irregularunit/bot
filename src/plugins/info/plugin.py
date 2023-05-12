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
from typing import TYPE_CHECKING, Union

import discord
from discord.ext import commands
from discord.utils import async_all
from typing_extensions import override

from src.imaging import RGB, ColorRepresentation
from src.models.discord.converter import MaybeMember
from src.shared import (
    ExceptionFactory,
    Plugin,
    SerenityEmbed,
    Stopwatch,
    CommandOption,
    for_command_callbacks,
)

from .utils import count_source_lines
from .views import AboutSerenityView

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Info",)


MaybeGuildMember = Union[discord.User, MaybeMember]
default_example = "`{0}{1} {2}`"


@for_command_callbacks(commands.cooldown(1, 5, commands.BucketType.user))
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
        extras={
            "options": (
                CommandOption(
                    option="None",
                    description="Shows information about Serenity.",
                ),
            ),
            "examples": default_example,
        },
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
        extras={
            "options": (
                CommandOption(
                    option="user",
                    description="The user whose avatar to show.",
                ),
            ),
            "examples": default_example,
        },
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
        name="names",
        aliases=("namehistory", "nh"),
        extras={
            "options": (
                CommandOption(
                    option="user",
                    description="The user whose username history to show.",
                ),
            ),
            "examples": default_example,
        },
    )
    async def username_history_command(
        self,
        ctx: SerenityContext,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(
                    """
                    SELECT
                        item_value,
                        changed_at
                    FROM
                        serenity_user_history
                    WHERE
                        snowflake = $1
                        AND
                        item_name = 'name'
                    ORDER BY
                        changed_at DESC
                    LIMIT
                        20
                    """,
                    user.id,
                )

        if not rows:
            raise ExceptionFactory.create_warning_exception(
                f"{user.display_name} has no username history."
            )

        embed = SerenityEmbed(
            description=(
                f"> Showing `{len(rows)}` of up to `20` changes.\n\n"
                f"{', '.join([row['item_value'] for row in rows])}"
            )
        )
        embed.set_author(
            name=f"{user.display_name}'s username history",
            icon_url=user.display_avatar,
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="color",
        aliases=("colour",),
        extras={
            "options": (
                CommandOption(
                    option="color",
                    description="The color to display.",
                ),
            ),
            "examples": default_example,
        },
    )
    async def color_command(
        self,
        ctx: SerenityContext,
        color: discord.Color = commands.param(
            converter=commands.ColorConverter,
        ),
    ) -> None:
        rgbcolor = RGB(*color.to_rgb())

        with Stopwatch() as timer:
            buffer = await self.serenity.to_thread(
                ColorRepresentation(256, 256, rgbcolor).raw
            )
            elapsed = timer.elapsed

        file = discord.File(buffer, filename="color.png")

        embed = SerenityEmbed(
            description=(
                f"**RGB**: `{color.r}`, `{color.g}`, `{color.b}`\n"
                f"**HEX**: `#{color.value:0>6x}`\n"
                f"> Rendered in `{elapsed:.2f}ms`"
            )
        )
        embed.set_author(
            name=f"Color: #{color.value:0>6x}",
            icon_url=f"attachment://color.png",
        )
        embed.set_image(url=f"attachment://{file.filename}")

        await ctx.send(file=file, embed=embed)

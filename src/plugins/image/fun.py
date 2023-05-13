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

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from src.imaging import RGB, Canvas, CanvasOption, ColorRepresentation
from src.imaging.utils import get_pride_type, pride_options
from src.shared import ExceptionFactory, MaybeMemberParam, SerenityEmbed, Stopwatch

from ._base import BaseImageManipulation
from .extras import ascii_extra, color_extra, palette_extra, pixelate_extra, pride_extra, triggered_extra

if TYPE_CHECKING:
    from src.models.discord import SerenityContext

__all__: tuple[str, ...] = ("FunImageManipulation",)


class FunImageManipulation(BaseImageManipulation):
    @commands.command(
        name="palette",
        aliases=("pal",),
        extras=palette_extra,
    )
    async def palette(self, ctx: SerenityContext, user: discord.User = MaybeMemberParam) -> None:
        user = user or ctx.author
        avatar = await self.get_avatar(user)

        with Stopwatch() as sw:
            discord_file = await Canvas(avatar).to_canvas(CanvasOption.PALETTE)
            elapsed_time = sw.elapsed

        embed = self.get_file_embed(
            user,
            discord_file.filename,
            title="avatar palette",
            description=f"> Generating took `{elapsed_time:.2f}` seconds.",
        )

        await ctx.send(embed=embed, file=discord_file)

    @commands.command(
        name="ascii",
        aliases=("asc",),
        extras=ascii_extra,
    )
    async def ascii(self, ctx: SerenityContext, user: discord.User = MaybeMemberParam) -> None:
        user = user or ctx.author
        avatar = await self.get_avatar(user)

        with Stopwatch() as sw:
            discord_file = await Canvas(avatar).to_canvas(CanvasOption.ASCII)
            elapsed_time = sw.elapsed

        embed = self.get_file_embed(
            user,
            discord_file.filename,
            title="avatar ascii",
            description=f"> Generating took `{elapsed_time:.2f}` seconds.",
        )

        await ctx.send(embed=embed, file=discord_file)

    @commands.command(
        name="pixelate",
        aliases=("pixel",),
        extras=pixelate_extra,
    )
    async def pixel(self, ctx: SerenityContext, user: discord.User = MaybeMemberParam) -> None:
        user = user or ctx.author
        avatar = await self.get_avatar(user)

        with Stopwatch() as sw:
            discord_file = await Canvas(avatar).to_canvas(CanvasOption.PIXEL)
            elapsed_time = sw.elapsed

        embed = self.get_file_embed(
            user,
            discord_file.filename,
            title="avatar pixel",
            description=f"> Generating took `{elapsed_time:.2f}` seconds.",
        )

        await ctx.send(embed=embed, file=discord_file)

    @commands.command(
        name="pride",
        aliases=("pr",),
        extras=pride_extra,
    )
    async def pride(self, ctx: SerenityContext, flag: str, user: discord.User = MaybeMemberParam) -> None:
        user = user or ctx.author
        avatar = await self.get_avatar(user)
        maybe_flag = get_pride_type(flag)

        if maybe_flag is None:
            raise ExceptionFactory.create_info_exception(
                f"Flag `{flag}` is not a valid pride flag.\nValid flags are: {'`, `'.join(pride_options)}"
            )

        with Stopwatch() as sw:
            discord_file = await Canvas(avatar).to_canvas(CanvasOption.PRIDE, option=maybe_flag)
            elapsed_time = sw.elapsed

        embed = self.get_file_embed(
            user,
            discord_file.filename,
            title="pride avatar",
            description=f"> Generating took `{elapsed_time:.2f}` seconds.",
        )

        await ctx.send(embed=embed, file=discord_file)

    @commands.command(
        name="triggered",
        aliases=("trigger",),
        extras=triggered_extra,
    )
    async def trigger(self, ctx: SerenityContext, user: discord.User = MaybeMemberParam) -> None:
        user = user or ctx.author
        avatar = await self.get_avatar(user)

        with Stopwatch() as sw:
            discord_file = await Canvas(avatar).to_canvas(CanvasOption.TRIGGER)
            elapsed_time = sw.elapsed

        embed = self.get_file_embed(
            user,
            discord_file.filename,
            title="triggered avatar",
            description=f"> Generating took `{elapsed_time:.2f}` seconds.",
        )

        await ctx.send(embed=embed, file=discord_file)

    @commands.command(
        name="color",
        aliases=("colour",),
        extras=color_extra,
    )
    async def color(
        self,
        ctx: SerenityContext,
        color: discord.Color = commands.param(
            converter=commands.ColorConverter(),
        ),
    ) -> None:
        rgb_color = RGB(*color.to_rgb())
        width = height = 256

        with Stopwatch() as sw:
            bufferd_io = await self.serenity.to_thread(ColorRepresentation(width, height, rgb_color).raw)
            elapsed_time = sw.elapsed

        file_name = self.generate_file_name()
        discord_file = discord.File(bufferd_io, filename=file_name)

        embed = SerenityEmbed(
            description=(
                f"**RGB**: `{color.r}`, `{color.g}`, `{color.b}`\n"
                f"**HEX**: `#{color.value:0>6x}`\n"
                f"> Rendered in `{elapsed_time:.2f}ms`"
            )
        )
        embed.set_author(
            name=f"Color: #{color.value:0>6x}",
            icon_url=f"attachment://{file_name}",
        )
        embed.set_image(url=f"attachment://{file_name}")

        await ctx.send(embed=embed, file=discord_file)

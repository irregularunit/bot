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

from typing import TYPE_CHECKING, Union
from uuid import uuid4

import discord
from discord.ext import commands
from discord.utils import async_all
from typing_extensions import override

from src.imaging import (
    AvatarCollage,
    Canvas,
    CanvasOption,
    FilePointer,
    PresenceGraph,
    PresenceHistory,
)
from src.imaging.utils import get_pride_type, pride_options
from src.models.discord.converter import MaybeMember
from src.shared import (
    ExceptionFactory,
    Plugin,
    SerenityEmbed,
    Stopwatch,
    for_command_callbacks,
)

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Imaging",)


@for_command_callbacks(commands.cooldown(1, 5, commands.BucketType.user))
class Imaging(Plugin):
    """The Imaging plugin provides image manipulation commands."""

    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity

    @override
    async def cog_check(self, ctx: SerenityContext) -> bool:
        checks = (commands.guild_only(),)
        return await async_all(
            check(ctx) for check in checks
        ) and await super().cog_check(ctx)

    async def _read_avatar(self, user: discord.User | discord.Member) -> bytes:
        try:
            return await user.display_avatar.read()
        except discord.HTTPException:
            raise ExceptionFactory.create_error_exception(
                f"Unable to read {user.display_name}'s avatar."
            )

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

    @commands.command(
        name="pallete",
        aliases=("pal",),
        help="Shows the color palette of a user's avatar.",
    )
    async def pallete_command(
        self,
        ctx: SerenityContext,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author
        avatar = await self._read_avatar(user)

        with Stopwatch() as timer:
            file = await Canvas(avatar).to_canvas(CanvasOption.PALLETE)
            elapsed = timer.elapsed

        embed = (
            SerenityEmbed(description=(f"> Generating took `{elapsed:.2f}` seconds.\n"))
            .set_author(
                name=f"{user.display_name}'s avatar pallete",
                icon_url=user.display_avatar,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(
        name="ascii",
        aliases=("asc",),
        help="Shows the ASCII representation of a user's avatar.",
    )
    async def ascii_command(
        self,
        ctx: SerenityContext,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author
        avatar = await self._read_avatar(user)

        with Stopwatch() as timer:
            file = await Canvas(avatar).to_canvas(CanvasOption.ASCII)
            elapsed = timer.elapsed

        embed = (
            SerenityEmbed(description=(f"> Generating took `{elapsed:.2f}` seconds.\n"))
            .set_author(
                name=f"{user.display_name}'s ascii avatar",
                icon_url=user.display_avatar,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(
        name="pixel",
        aliases=("px",),
        help="Shows the pixel representation of a user's avatar.",
    )
    async def paint_command(
        self,
        ctx: SerenityContext,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author
        avatar = await self._read_avatar(user)

        with Stopwatch() as timer:
            file = await Canvas(avatar).to_canvas(CanvasOption.PIXEL)
            elapsed = timer.elapsed

        embed = (
            SerenityEmbed(description=(f"> Generating took `{elapsed:.2f}` seconds.\n"))
            .set_author(
                name=f"{user.display_name}'s pixel avatar",
                icon_url=user.display_avatar,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(
        name="trigger",
        aliases=("trg",),
        help="Shows the triggered representation of a user's avatar.",
    )
    async def trigger_command(
        self,
        ctx: SerenityContext,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author
        avatar = await self._read_avatar(user)

        with Stopwatch() as timer:
            file = await Canvas(avatar).to_canvas(CanvasOption.TRIGGER)
            elapsed = timer.elapsed

        embed = (
            SerenityEmbed(description=(f"> Generating took `{elapsed:.2f}` seconds.\n"))
            .set_author(
                name=f"{user.display_name}'s triggered avatar",
                icon_url=user.display_avatar,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(
        name="presencegraph",
        aliases=("ps", "presence"),
        help="Shows the presence graph of a user.",
    )
    async def presence_graph_command(
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
                records = await conn.fetch(
                    """
                    SELECT
                        status,
                        changed_at
                    FROM
                        serenity_user_presence
                    WHERE
                        snowflake = $1
                    AND
                        changed_at > NOW() - INTERVAL '7 days'
                    ORDER BY
                        changed_at ASC
                    """,
                    user.id,
                )

        if not records:
            raise ExceptionFactory.create_warning_exception(
                f"{user.display_name} has no presence history."
            )

        dates = [record["changed_at"] for record in records]
        statuses = [record["status"] for record in records]
        data = PresenceHistory(dates=dates, statuses=statuses)

        with Stopwatch() as timer:
            buffer = await PresenceGraph(data).buffer()
            elapsed = timer.elapsed

        file = discord.File(buffer, filename=f"{uuid4()}.png")

        embed = (
            SerenityEmbed(
                description=(
                    f"> Generating took `{elapsed:.2f}` seconds.\n"
                    f"> Showing your `weekly` presence history."
                )
            )
            .set_author(
                name=f"{user.display_name}'s presence history",
                icon_url=user.display_avatar,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(
        name="pride",
        aliases=("pr",),
        help="Converts your avatar to a pride one.",
    )
    async def pride_command(
        self,
        ctx: SerenityContext,
        option: str,
        user: discord.User = commands.param(
            converter=Union[discord.User, MaybeMember],
            default=None,
            displayed_default="you",
        ),
    ) -> None:
        user = user or ctx.author
        avatar = await self._read_avatar(user)
        flag = get_pride_type(option)

        if flag is None:
            options = ", ".join(f"`{k}`" for k in pride_options)
            raise ExceptionFactory.create_error_exception(
                f"Invalid pride option. Try one of these: `{options}`."
            )

        with Stopwatch() as timer:
            file = await Canvas(avatar).to_canvas(CanvasOption.PRIDE, option=flag)
            elapsed = timer.elapsed

        embed = (
            SerenityEmbed(description=(f"> Generating took `{elapsed:.2f}` seconds.\n"))
            .set_author(
                name=f"{user.display_name}'s pride avatar",
                icon_url=user.display_avatar,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        await ctx.send(embed=embed, file=file)

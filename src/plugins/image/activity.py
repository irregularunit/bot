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

from datetime import datetime
from typing import TYPE_CHECKING, Tuple

import discord
from discord.ext import commands

from src.imaging import AvatarCollage, FilePointer, PresenceGraph, PresenceHistory
from src.shared import ExceptionFactory, MaybeMemberParam, Stopwatch

from ._base import BaseImageManipulation
from .extras import avatar_history_extra, presence_graph_extra

if TYPE_CHECKING:
    from src.models.discord import SerenityContext

__all__: Tuple[str, ...] = ("ActivityHistory",)


class ActivityHistory(BaseImageManipulation):
    @commands.command(
        name="avatarhistory",
        aliases=("avh", "avhy"),
        extras=avatar_history_extra,
    )
    async def avatar_history(self, ctx: SerenityContext, user: discord.User = MaybeMemberParam) -> None:
        user = user or ctx.author
        pointer = FilePointer(user.id)

        if pointer.empty:
            raise ExceptionFactory.create_warning_exception(f"{user.display_name} has no avatar history.")

        with Stopwatch() as sw:
            buffered_io = await AvatarCollage(pointer).buffer()
            elapsed_time = sw.elapsed

        filename = self.generate_file_name()
        file = discord.File(buffered_io, filename=filename)

        embed = self.get_file_embed(
            user,
            filename,
            title="avatar history",
            description=(
                f"> Generating took `{elapsed_time:.2f}` seconds.\n"
                f"> Showing `{len(pointer)}` of up to `100` changes."
            ),
        )

        await ctx.send(file=file, embed=embed)

    @commands.command(
        name="presencehistory",
        aliases=("ps", "pshy"),
        extras=presence_graph_extra,
    )
    async def presence_history(self, ctx: SerenityContext, user: discord.User = MaybeMemberParam) -> None:
        user = user or ctx.author

        query = """
            SELECT
                status,
                changed_at
            FROM
                serenity_user_presence
            WHERE
                snowflake = $1
            AND
                changed_at > (NOW() - INTERVAL '7 days')
            ORDER BY
                changed_at ASC
        """

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                results = await conn.fetch(query, user.id)

        if not results:
            raise ExceptionFactory.create_warning_exception(f"{user.display_name} has no presence history.")

        dates: list[datetime] = [result["changed_at"] for result in results]
        statuses: list[str] = [result["status"] for result in results]

        presence = PresenceHistory(dates=dates, statuses=statuses)

        with Stopwatch() as sw:
            buffered_io = await PresenceGraph(presence).buffer()
            elapsed_time = sw.elapsed

        filename = self.generate_file_name()
        file = discord.File(buffered_io, filename=filename)

        embed = self.get_file_embed(
            user,
            filename,
            title="presence history",
            description=(f"> Generating took `{elapsed_time:.2f}` seconds.\n> Showing your `weekly` presence history."),
        )

        await ctx.send(file=file, embed=embed)

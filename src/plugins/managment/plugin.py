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

from io import StringIO
from logging import getLogger
from typing import TYPE_CHECKING, Optional, Tuple

from discord.ext import commands
from typing_extensions import override

from src.shared import ExceptionFactory, Plugin, for_command_callbacks

from .extras import prefix_extra, prefix_list_extra, prefix_remove_extra

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity

__all__: Tuple[str, ...] = ("Managment",)

logger = getLogger(__name__)


@for_command_callbacks(commands.cooldown(1, 5, commands.BucketType.user))
class Managment(Plugin):
    @override
    def __init__(self, serenity: Serenity):
        self.serenity = serenity

    @commands.has_guild_permissions(manage_guild=True)
    @commands.group(
        name="prefix",
        aliases=("prefixes",),
        invoke_without_command=True,
        extras=prefix_extra,
        brief="Manage the prefixes for this guild.",
    )
    async def prefix(self, ctx: SerenityContext, *, prefix: Optional[str] = None) -> None:
        assert ctx.guild is not None

        if prefix is None:
            command = self.serenity.get_command("prefix list")
            return await ctx.invoke(command)  # type: ignore

        invalid_id_prefixes = [
            f"<@{ctx.me.id}>",
            f"<@!{ctx.me.id}>",
        ]

        if prefix in invalid_id_prefixes:
            raise ExceptionFactory.create_error_exception(
                f"Invalid prefix: `{prefix}`. This prefix is reserved for mentioning me."
            )

        guild = await self.serenity.get_or_create_guild(ctx.guild.id)
        updated_guild = await self.serenity.model_manager.add_guild_prefix(guild, prefix)

        self.serenity.set_guild(updated_guild)

        await ctx.maybe_reply(f"Successfully added `{prefix}` to the list of prefixes.")

    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command(name="list", aliases=("ls",), extras=prefix_list_extra, brief="List the prefixes for this guild.")
    async def prefix_list(self, ctx: SerenityContext) -> None:
        assert ctx.guild is not None

        guild = await self.serenity.get_or_create_guild(ctx.guild.id)

        buffered_io = StringIO()

        buffered_io.write('```prolog\n')
        buffered_io.write(f'=== Prefixes for "{ctx.guild.name}" ===\n')
        buffered_io.write("\nPrefixes:\n")

        if len(guild.prefixes) == 0:
            buffered_io.write("No prefixes have been set for this guild.\n")

        for prefix in guild.prefixes:
            buffered_io.write(f"・ '{prefix}'\n")

        buffered_io.write('```')

        await ctx.maybe_reply(buffered_io.getvalue())

    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command(name="remove", aliases=("rm",), extras=prefix_remove_extra, brief="Remove a prefix for this guild.")
    async def prefix_remove(self, ctx: SerenityContext, *, prefix: str) -> None:
        assert ctx.guild is not None

        guild = await self.serenity.get_or_create_guild(ctx.guild.id)
        updated_guild = await self.serenity.model_manager.remove_guild_prefix(guild, prefix)

        self.serenity.set_guild(updated_guild)

        await ctx.maybe_reply(f"Successfully removed `{prefix}` from the list of prefixes.")

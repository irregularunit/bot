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
from typing_extensions import override

from src.shared import Plugin

from .handlers import get_message

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Errors",)


class Errors(Plugin):
    serenity: Serenity
    snail: str

    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity
        self.snail = "\N{SNAIL}"

    @Plugin.listener("on_command_error")
    async def error_listener(self, ctx: SerenityContext, error: commands.CommandError) -> None:
        if not ctx.guild:
            return

        if isinstance(error, commands.CommandOnCooldown):
            if await self.serenity.redis.exists(f"{ctx.author.id}:RateLimit:Command"):
                return

            await self.serenity.redis.setex(
                f"{ctx.author.id}:RateLimit:Command",
                int(error.retry_after) + 1,
                "command cooldown",
            )

            try:
                return await ctx.message.add_reaction(self.snail)
            except discord.HTTPException:
                return

        hint = get_message(ctx, error)
        send = ctx.channel.permissions_for(ctx.guild.me).send_messages

        if send and hint is not None:
            try:
                await ctx.send(hint)
            except discord.HTTPException:
                pass

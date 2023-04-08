"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import ButtonStyle, Interaction, Member, Message, User, utils
from discord.ext import commands
from discord.ui import Button, View, button

from utils import BaseExtension, async_all, for_all_callbacks, get_random_emoji

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("Transparency",)

log: logging.Logger = logging.getLogger(__name__)


class SafetyPrompt(View):
    """A view that asks the user to confirm an action."""

    def __init__(self, user: Member | User) -> None:
        super().__init__()
        self.user: Member | User = user
        self.confirmed: bool = False

    @button(label="Yes", style=ButtonStyle.green)
    async def yes(self, interaction: Interaction, button: Button) -> None:
        self.confirmed = True
        await interaction.response.send_message(
            "Thank you for confirming this action. Your request will be processed shortly.", ephemeral=True
        )
        self.stop()

    @button(label="No", style=ButtonStyle.red)
    async def no(self, interaction: Interaction, button: Button) -> None:
        await interaction.response.send_message("Action has been cancelled. No changes have been made.", ephemeral=True)
        self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user.id


@for_all_callbacks(commands.cooldown(1, 3, commands.BucketType.user))
class Transparency(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        checks = [commands.guild_only()]
        return await async_all(check(ctx) for check in checks)

    @commands.group(name="delete", aliases=("rm",), invoke_without_command=False)
    async def delete(self, ctx: Context) -> None:
        ...

    @delete.command(name="recordset", aliases=("rs",))
    async def delete_recordset(self, ctx: Context) -> None:
        user = await self.bot.manager.get_or_create_user(ctx.author.id)

        prompt = SafetyPrompt(ctx.author)
        message: Message | None = await ctx.safe_send(
            "Are you sure you want to delete your data? This action is irreversible.", view=prompt
        )

        if not message:
            return

        await prompt.wait()

        if prompt.confirmed:
            await user.delete(self.bot.pool)

            if (cached_user := self.bot.cached_users.get(user.id)) is not None:
                self.bot.cached_users.pop(cached_user.id)

            log.getChild("delete").info(f"Deleted user {user.id} ({ctx.author.name})")
            await message.edit(content="Your data has been deleted. Thank you for using our services.", view=None)
        else:
            await message.edit(content="Action has been cancelled.", view=None)

    @commands.command(name="suggest", aliases=("suggestion",))
    async def suggest(self, ctx: Context, *, suggestion: str) -> None:
        owner = self.bot.get_user(self.bot.config.client_owner) or await self.bot.fetch_user(
            self.bot.config.client_owner
        )

        prompt = SafetyPrompt(ctx.author)
        message: Message | None = await ctx.safe_send(
            f"Are you sure you want to send this suggestion?\n" f">>> {suggestion} ...\n", view=prompt
        )

        if not message:
            return

        await prompt.wait()

        if prompt.confirmed:
            await owner.send(
                f"**{get_random_emoji()} New suggestion from {ctx.author} ({ctx.author.id}):**\n"
                f"**Date:** {utils.format_dt(utils.utcnow(), style='F')}\n"
                f">>> {suggestion}"
            )

        await message.delete()


async def setup(bot: Bot) -> None:
    await bot.add_cog(Transparency(bot))

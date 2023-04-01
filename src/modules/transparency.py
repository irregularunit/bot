"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import ButtonStyle, Interaction, Message
from discord.ext import commands
from discord.ui import Button, View, button

from models import User
from utils import BaseExtension, for_all_callbacks

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("Transparency",)

log: logging.Logger = logging.getLogger(__name__)


class SafetyPrompt(View):
    def __init__(self, user: User) -> None:
        super().__init__()
        self.user: User = user
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


@for_all_callbacks(commands.cooldown(1, 3, commands.BucketType.user))
class Transparency(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    @commands.group(name="delete", aliases=("rm",), invoke_without_command=False)
    async def delete(self, ctx: Context) -> None:
        ...

    @delete.command(name="recordset", aliases=("rs",))
    async def delete_recordset(self, ctx: Context) -> None:
        user: User = await self.bot.manager.get_or_create_user(ctx.author.id)

        prompt = SafetyPrompt(user)
        message: Message | None = await ctx.safe_send(
            "Are you sure you want to delete your data? This action is irreversible.", view=prompt
        )

        if not message:
            return

        await prompt.wait()

        if prompt.confirmed:
            await user.delete(self.bot.pool)
            if user.id in self.bot.cached_users:
                self.bot.cached_users.pop(user.id)

            await message.edit(content="Your data has been deleted. Thank you for using our services.", view=None)
        else:
            await message.edit(content="Action has been cancelled.", view=None)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Transparency(bot))
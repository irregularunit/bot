"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

# Most of this code is copied from src/views/avatar.py

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ui import View

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("PluginView",)

class PluginView(View):
    def __init__(
        self, ctx: Context, /, *, member: discord.Member | discord.User, timeout: Optional[float] = 60.0
    ) -> None:
        super().__init__(timeout=timeout)
        self.ctx: Context = ctx
        self.bot: Bot = ctx.bot

        self.member: discord.Member | discord.User = member
        self.message: Optional[discord.Message] = None

    def disable_view(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                # This check is purly done for type checking purposes
                # and is not needed for the code to work.
                if hasattr(item, "disabled"):
                    # Same as: item.disabled = True
                    # But this is the "proper" way to do it.
                    setattr(item, "disabled", True)

    async def on_timeout(self) -> None:
        self.disable_view()
        if self.message is not None:
            await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True

        await interaction.response.send_message("You cannot use this, sorry. :(", ephemeral=True)
        return False
"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ui import View

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("PluginView",)


class PluginView(View):
    """A view for the plugin command.

    Parameters
    ----------
    ctx: `Context`
        The context of the command.
    member: `discord.Member | discord.User`
        The member to be added to the plugin.
    timeout: `Optional[float]`
        The timeout of the view.
    """

    def __init__(
        self,
        ctx: Context,
        /,
        *,
        member: discord.Member | discord.User,
        timeout: Optional[float] = 60.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.ctx: Context = ctx
        self.bot: Bot = ctx.bot

        self.member: discord.Member | discord.User = member
        self.message: Optional[discord.Message] = None

    def disable_view(self) -> None:
        """Disable the view."""
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                # This check is purly done for type checking purposes
                # and is not needed for the code to work.
                if hasattr(item, "disabled"):
                    # Same as: item.disabled = True
                    # But this is the "proper" way to do it.
                    setattr(item, "disabled", True)

    async def on_timeout(self) -> None:
        """Called when the view times out."""
        self.disable_view()
        if self.message is not None:
            await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction[Bot]) -> bool:
        """Check if the interaction is valid.

        Parameters
        ----------
        interaction: `discord.Interaction[Bot]`
            The interaction to check.

        Returns
        -------
        `bool`
            Whether the interaction is valid.
        """
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True

        await interaction.response.send_message("You cannot use this, sorry. :(", ephemeral=True)
        return False

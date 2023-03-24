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

from models import EmbedBuilder
from .buttons import CollageAvatarButton

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context


class AvatarHistoryView(View):
    def __init__(self, ctx: Context, /, *, member: discord.Member | discord.User, timeout: Optional[float] = 60.0) -> None:
        super().__init__(timeout=timeout)
        self.ctx: Context = ctx
        self.bot: Bot = ctx.bot

        self.member: discord.Member | discord.User = member
        self.message: Optional[discord.Message] = None

        self.cached_avatars: list[str] = []
        self.index: int = 0

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

    async def fetch_avatar_history_items(self) -> list[str]:
        query = "SELECT item_value FROM item_history WHERE uid = $1 AND item_type = $2"
        res = await self.bot.pool.fetch(query, self.member.id, "avatar")
        ret = [row["item_value"] for row in res]

        self.cached_avatars = ret
        return ret
    
    def setup_by_index(self, index: int) -> EmbedBuilder:
        length_hint: int = len(self.cached_avatars)

        # The modulo operator (%) is being used to ensure that the 
        # index variable stays within the bounds of the self.cached_avatars list.
        
        # Why is this useful? Consider the case where self.index is 
        # larger than length_hint. Without the modulo operation, we would end up 
        # with an index that's out of range and would raise an IndexError. However, 
        # by using the modulo operation, we effectively "wrap around" to the 
        # beginning of the list and start again from the beginning. This ensures 
        # that we always have a valid index within the bounds of the list.
        index = self.index % length_hint

        self.previous_avatar.disabled = bool(index == 0)
        self.next_avatar.disabled = bool(index == length_hint - 1)

        embed: EmbedBuilder = (
            EmbedBuilder.factory(self.ctx)
            .set_author(
                name=f"{self.member or self.ctx.author}'s avatar history",
                icon_url=self.ctx.me.display_avatar)
            .set_image(url=self.cached_avatars[index])
            .set_footer(text=f"Avatar {index + 1} of {length_hint}")
        )
        return embed
    
    async def edit_to_current_index(self, interaction: discord.Interaction) -> None:
        element: EmbedBuilder = self.setup_by_index(self.index)

        if isinstance(element, EmbedBuilder):
            self.message = await interaction.response.edit_message(embed=element, view=self)
        else:
            raise TypeError(f"Expected EmbedBuilder, got {type(element)!r}")
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_avatar(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_to_current_index(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_avatar(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_to_current_index(interaction)

    async def start(self) -> Optional[discord.Message]:
        self.cached_avatars = await self.fetch_avatar_history_items()
        self.add_item(CollageAvatarButton(label="Collage", style=discord.ButtonStyle.blurple))

        if not self.cached_avatars:
            return await self.ctx.send(
                embed=EmbedBuilder.factory(
                self.ctx,
                title=f"{self.member or self.ctx.author}'s has no avatar histor",
            ).set_image(url=self.member.display_avatar)
        )

        embed: EmbedBuilder = self.setup_by_index(self.index)
        self.message = await self.ctx.send(embed=embed, view=self)

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any, Optional

import discord
from PIL import Image

from models import EmbedBuilder
from pil import AvatarCollage, AvatarCollageType

__all__: tuple[str, ...] = ("CollageAvatarButton",)


class CollageAvatarButton(discord.ui.Button):
    """A button that creates a collage of the user's avatars.

    Parameters
    ----------
    **kwargs: `Any`
        The keyword arguments to pass to the super class.

    Attributes
    ----------
    disabled: `bool`
        Whether the button is disabled or not.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.disabled = False

    async def create_collage(self, images: list[Image.Image]) -> discord.File:
        collage_entry: AvatarCollageType = AvatarCollageType(images)
        collage: AvatarCollage = AvatarCollage(collage_entry)
        return await asyncio.to_thread(collage.create)

    async def get_member_collage(
        self, member: discord.Member | discord.User
    ) -> Optional[discord.File]:
        """Get the collage of the user's avatars.

        Parameters
        ----------
        member: `Union[discord.Member, discord.User]`
            The member to get the collage for.

        Returns
        -------
        `Optional[discord.File]`
            The collage.
        """
        if self.view is None:
            raise AssertionError

        results = await self.view.bot.pool.fetch(
            "SELECT * FROM avatar_history WHERE uuid = $1 ORDER BY changed_at DESC",
            member.id,
        )
        if not results:
            return None

        images: list[Image.Image] = []
        for result in results:
            with Image.open(BytesIO(result["avatar"])) as avatar:
                images.append(avatar.resize((256, 256)).convert("RGBA"))

        return await self.create_collage(images)

    async def callback(self, interaction: discord.Interaction) -> None:
        """The callback for the button.

        Parameters
        ----------
        interaction: `discord.Interaction`
            The interaction.
        """
        if self.view is None:
            raise AssertionError

        view = self.view
        self.disabled = True

        file: discord.File | None = await self.get_member_collage(view.member)

        embed: EmbedBuilder = EmbedBuilder.factory(view.ctx)
        embed.set_image(url=f"attachment://{file.filename if file else 'collage.webp'}")

        if not file:
            embed.set_author(name="No avatar history found. 🫠")
            embed.set_image(url=view.member.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            embed.set_author(name=f"Avatar collage for {view.member.display_name}. 🥺")
            self.view.message = await interaction.response.edit_message(
                embed=embed, attachments=[file], view=view
            )

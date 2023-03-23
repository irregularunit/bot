"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import math
from io import BytesIO
from typing import TYPE_CHECKING, Any, Optional

import discord
from PIL import Image

from models import EmbedBuilder

if TYPE_CHECKING:
    from ..avatar import AvatarHistoryView


class CollageAvatarButton(discord.ui.Button):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.disabled = False

    def compute_grid_size(self, amount: int) -> int:
        return int(amount**0.5) + 1 if amount**0.5 % 1 else int(amount**0.5)

    def create_collage(self, images: list[Image.Image], old: bool = True) -> BytesIO:
        grid_size = self.compute_grid_size(len(images))
        rows: int = math.ceil(math.sqrt(len(images)))

        # Read the following code on your own risk.
        # I forgot why I did it this way. And I don't want to know.
        # Feel free to rewrite it if you want.
        width = height = 256 * rows

        if old:
            with Image.new("RGBA", (width, height), (0, 0, 0, 0)) as collage:
                times_x = times_y = final_x = final_y = 0
                for avatar in images:
                    if times_x == grid_size:
                        times_y += 1
                        times_x = 0

                    x, y = times_x * 256, times_y * 256
                    collage.paste(avatar, (x, y))

                    final_x, final_y = max(x, final_x), max(y, final_y)
                    times_x += 1

                collage: Image.Image = collage.crop((0, 0, final_x + 256, final_y + 256))

                buffer: BytesIO = BytesIO()
                collage.save(buffer, format="webp")
                buffer.seek(0)
                return buffer
        else:
            # Currently testing this new method. Might be adjusted in the future.
            # For now it seems to work just fine.
            with Image.new("RGBA", (width, height), (0, 0, 0, 0)) as collage:
                for i, avatar in enumerate(images):
                    x, y = (i % rows) * 256, (i // rows) * 256
                    collage.paste(avatar, (x, y))

                last_x, last_y = divmod(len(images) - 1, rows)
                last_height, last_width = (last_x + 1) * 256, (last_y + 1) * 256
                collage = collage.crop((0, 0, last_width, last_height))

                buffer: BytesIO = BytesIO()
                collage.save(buffer, format="webp")
                buffer.seek(0)
                return buffer

    async def get_member_collage(self, member: discord.Member | discord.User) -> Optional[discord.File]:
        assert self.view is not None

        results = await self.view.bot.pool.fetch(
            "SELECT * FROM avatar_history WHERE uid = $1 ORDER BY changed_at DESC", member.id
        )
        if not results:
            return None

        images: list[Image.Image] = []
        for result in results:
            with Image.open(BytesIO(result["avatar"])) as avatar:
                images.append(avatar.resize((256, 256)).convert("RGBA"))

        buffer: BytesIO = await self.view.bot.to_thread(self.create_collage, images, old=False)
        return discord.File(buffer, filename="collage.webp")

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None

        # Note for my future self:
        # Create a type for views that use this button.
        view: AvatarHistoryView = self.view
        embed = EmbedBuilder.factory(view.ctx)
        embed.set_image(url="attachment://collage.webp")
        embed.set_footer(text=f"Avatar collage of {view.member}")

        file: discord.File | None = await self.get_member_collage(view.member)

        if not file:
            embed.set_author(name="No avatar history found. 🫠", icon_url=view.ctx.me.display_avatar)
            embed.set_image(url=view.member.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            embed.set_author(name=f"Avatar collage from {view.member.display_name}. 🥺", icon_url=view.ctx.me.display_avatar)
            self.view.disable_view()
            self.view.message = await interaction.response.edit_message(embed=embed, attachments=[file], view=view)

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
from uuid import uuid4

import discord
from typing_extensions import override

from src.shared import ExceptionFactory, Plugin, SerenityEmbed

if TYPE_CHECKING:
    from src.models.serenity import Serenity

__all__: tuple[str, ...] = ("BaseImageManipulation",)


class BaseImageManipulation(Plugin):
    serenity: Serenity

    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity

    async def get_avatar(self, user: discord.User | discord.Member) -> bytes:
        try:
            return await user.display_avatar.read()
        except discord.HTTPException:
            raise ExceptionFactory.create_critical_exception(
                f"Unable to retrieve avatar for {user}")

    def get_file_embed(
        self,
        user: discord.User | discord.Member,
        file_name: str,
        *,
        title: str,
        description: str = "",
    ) -> SerenityEmbed:
        embed = (
            SerenityEmbed(description=description)
            .set_author(name=f"{user}'s {title}", icon_url=user.display_avatar.url)
            .set_image(url=f"attachment://{file_name}")
        )
        return embed

    def generate_file_name(self, file_extension: str = ".png") -> str:
        return f"{uuid4()}{file_extension}"

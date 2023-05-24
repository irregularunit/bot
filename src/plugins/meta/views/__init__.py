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

from typing import Self

from discord import ButtonStyle, Interaction
from discord.ui import Button, button

from src.shared import SerenityView

from ..utils import GITHUB_URL

__all__: tuple[str, ...] = ("AboutSerenityView",)


class AboutSerenityView(SerenityView):
    def __init__(
        self,
        owner: int,
        /,
        link: str,
        label: str,
        *,
        timeout: int = 60,
    ) -> None:
        super().__init__(timeout=timeout)

        self.owner = owner
        self.link = link
        self.label = label

        buttons: list[Button[Self]] = [
            Button(label="GitHub", style=ButtonStyle.link, url=GITHUB_URL),
            Button(label=self.label, style=ButtonStyle.link, url=self.link),
        ]

        for button in buttons:
            self.add_item(button)

    @button(label="Close", style=ButtonStyle.danger)
    async def close_button(self, interaction: Interaction, _) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id == self.owner:
            await interaction.response.send_message("Only the bot owner can use this view.", ephemeral=True)
            return False

        return True

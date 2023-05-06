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

from discord import ButtonStyle, Interaction
from discord.ui import Button

from src.shared import SerenityEmbed, SerenityView

if TYPE_CHECKING:
    from src.models.discord import SerenityContext

__all__: tuple[str, ...] = ("PartialMessageView",)


class PartialMessageView(SerenityView):
    def __init__(
        self, embed: SerenityEmbed, /, *, jump_url: str, timeout: int = 60
    ) -> None:
        super().__init__(timeout=timeout)
        self.embed = embed
        self.jump_url = jump_url

        self.add_item(
            Button(
                label="Jump to Message",
                style=ButtonStyle.link,
                url=self.jump_url,
            )
        )

    async def send_to(self, destination: SerenityContext | Interaction) -> None:
        if isinstance(destination, SerenityContext):
            await destination.send(embed=self.embed, view=self)
        else:
            await destination.response.edit_message(embed=self.embed, view=self)

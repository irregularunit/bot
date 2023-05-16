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

from typing import TYPE_CHECKING, Final, Tuple

from discord import ButtonStyle, Interaction
from discord.ui import Button

if TYPE_CHECKING:
    from .views._base import ABCHelpCommandView

__all__: Tuple[str, ...] = (
    "StartEmoji",
    "DisableEmoji",
    "ToStart",
    "DisableButton",
)

StartEmoji: Final[str] = "🧭"
DisableEmoji: Final[str] = "🗑️"


class ToStart(Button["ABCHelpCommandView"]):
    __slots__: Tuple[str, ...] = ("bot", "parent")

    def __init__(self, *, parent: ABCHelpCommandView) -> None:
        self.bot = parent.bot
        self.parent = parent
        super().__init__(style=ButtonStyle.blurple, emoji=StartEmoji)

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.edit_message(content=self.parent.to_string(), view=self.parent)


class DisableButton(Button["ABCHelpCommandView"]):
    __slots__: Tuple[str, ...] = ("bot", "parent")

    def __init__(self, *, parent: ABCHelpCommandView) -> None:
        self.bot = parent.bot
        self.parent = parent
        super().__init__(style=ButtonStyle.red, emoji=DisableEmoji)

    async def callback(self, interaction: Interaction) -> None:
        for child in self.parent.children:
            setattr(child, "disabled", True)

        self.parent.stop()

        await interaction.response.edit_message(content="Interaction has been closed.", view=self.parent)

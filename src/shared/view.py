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

from copy import deepcopy
from typing import TYPE_CHECKING, List, Optional, Tuple

from discord import ButtonStyle, Client, File, Interaction, NotFound
from discord.ui import Button, Item, View, button

if TYPE_CHECKING:
    from ..models.serenity import Serenity
    from .embed import SerenityEmbed

__all__: Tuple[str, ...] = ("SerenityView", "SerenityPaginator", "PaginatorEntry", "SerenityConfirmPrompt")

UNKNOWN_INTERACTION = 10062


class SerenityView(View):
    async def on_error(
        self,
        interaction: Interaction[Client],
        error: Exception,
        item: Item[View],
    ) -> None:
        # Remove uselss noise from the logs.
        if isinstance(error, NotFound):
            return

        if getattr(error, "code", None) == UNKNOWN_INTERACTION:
            return

        await super().on_error(interaction, error, item)

    @property
    def has_children(self) -> bool:
        return bool(self.children)

    def disable_children(self) -> None:
        if self.has_children is False:
            raise ValueError("This view has no children to disable.")

        for child in self.children:
            setattr(child, "disabled", True)


class PaginatorEntry:
    __slots__ = ("content", "embed", "_files")

    def __init__(
        self,
        *,
        content: Optional[str] = None,
        embed: Optional[SerenityEmbed] = None,
        files: Optional[List[File]] = None,
    ) -> None:
        self.content = content
        self.embed = embed
        self._files = files or []

    @property
    def files(self):
        """Copy of file for reusability."""
        return [deepcopy(f) for f in self._files]


class SerenityPaginator(SerenityView):
    __slots__ = ("bot", "items", "page", "labels")

    page: int
    bot: Serenity
    labels: dict[str, str]
    items: Tuple[PaginatorEntry, ...]

    def __init__(self, bot: Serenity, *items: PaginatorEntry) -> None:
        super().__init__()
        self.page = 0
        self.bot = bot
        self.items = items
        self.labels = {
            "first": "<<",
            "back": "<",
            "next": ">",
            "skip": ">>",
        }

        for child in self.children:
            if isinstance(child, Button):
                setattr(child, "style", ButtonStyle.primary)
                child.label = self.labels[child.callback.callback.__name__]  # type: ignore

    async def edit(self, interaction: Interaction, *, page: int) -> None:
        self.page = page
        unit = self.items[page]
        await interaction.response.edit_message(content=unit.content, embed=unit.embed, attachments=unit.files)

    @button()
    async def first(self, interaction: Interaction, _) -> None:
        await self.edit(interaction, page=0)

    @button()
    async def back(self, interaction: Interaction, _) -> None:
        await self.edit(interaction, page=max(self.page - 1, 0))

    @button()
    async def next(self, interaction: Interaction, _) -> None:
        await self.edit(interaction, page=min(self.page + 1, len(self.items) - 1))

    @button()
    async def skip(self, interaction: Interaction, _) -> None:
        await self.edit(interaction, page=len(self.items) - 1)


class SerenityConfirmPrompt(SerenityView):
    __slots__ = ("bot", "author", "message", "_value")

    bot: Serenity
    author: int
    message: str
    _value: bool

    def __init__(self, bot: Serenity, author: int, *, message: str) -> None:
        super().__init__()
        self.bot = bot
        self.author = author
        self.message = message
        self._value = False

    @property
    def value(self) -> bool:
        return self._value

    @button(label="Confirm", style=ButtonStyle.success)
    async def confirm(self, interaction: Interaction, _) -> None:
        self._value = True
        self.stop()

    @button(emoji="❌", style=ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, _) -> None:
        self._value = False
        self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.author:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return False

        return True

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

__all__: Tuple[str, ...] = ("SerenityView", "SerenityPaginator", "PaginatorEntry")

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

    bot: Serenity
    items: Tuple[PaginatorEntry, ...]
    page: int
    labels: dict[str, str]

    def __init__(self, bot: Serenity, *items: PaginatorEntry) -> None:
        super().__init__()
        self.bot = bot
        self.items = items
        self.page = 0
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

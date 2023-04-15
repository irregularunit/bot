"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Optional

from discord import ButtonStyle, File, Interaction
from discord.ui import Button, View, button

from models import EmbedBuilder

if TYPE_CHECKING:
    from bot import Bot

__all__: tuple[str, ...] = ("Item", "Paginator")


class Item:
    """A unit of an item for the paginator.
    
    Parameters
    ----------
    content: `Optional[str]`
        The content of the item.
    embed: `Optional[EmbedBuilder]`
        The embed of the item.
    files: `Optional[list[File]]`
        The files of the item.

    Attributes
    ----------
    content: `Optional[str]`
        The content of the item.
    embed: `Optional[EmbedBuilder]`
        The embed of the item.
    files: `list[File]`
        The files of the item.
    """
    __slots__ = ("content", "embed", "_files")

    def __init__(
        self,
        *,
        content: Optional[str] = None,
        embed: Optional[EmbedBuilder] = None,
        files: Optional[list[File]] = None,
    ) -> None:
        self.content = content
        self.embed = embed
        self._files = files or []

    @property
    def files(self):
        """Copy of file for reusability."""
        return [deepcopy(f) for f in self._files]


class Paginator(View):
    """Simple embed and file paginator view
    
    Parameters
    ----------
    bot: `Bot`
        The bot instance.
    *items: `Item`
        The items to paginate.

    Attributes
    ----------
    bot: `Bot`
        The bot instance.
    items: `tuple[Item, ...]`
        The items to paginate.
    page: `int`
        The current page.
    labels: `dict[str, str]`
        The labels for the buttons.
    """

    def __init__(self, bot: Bot, *items: Item) -> None:
        super().__init__()
        self.bot: Bot = bot
        self.items: tuple[Item, ...] = items
        self.page = 0
        self.labels: dict[str, str] = {
            "first": "<<",
            "back": "<",
            "next": ">",
            "skip": ">>",
        }

        for child in self.children:
            if isinstance(child, Button):
                if child.style == ButtonStyle.secondary:
                    child.style = ButtonStyle.primary
                child.label = self.labels[child.callback.callback.__name__]

    async def edit(self, interaction: Interaction, *, page: int) -> None:
        """Edit the message with the new page.

        Parameters
        ----------
        interaction: `Interaction`
            The interaction to edit.
        page: `int`
            The page to edit to.
        """
        self.page = page
        unit = self.items[page]
        await interaction.response.edit_message(
            content=unit.content, embed=unit.embed, attachments=unit.files
        )

    @button()
    async def first(self, interaction: Interaction, btn: Button[Paginator]) -> None:
        await self.edit(interaction, page=0)

    @button()
    async def back(self, interaction: Interaction, btn: Button[Paginator]) -> None:
        await self.edit(interaction, page=max(self.page - 1, 0))

    @button()
    async def next(self, interaction: Interaction, btn: Button[Paginator]) -> None:
        await self.edit(interaction, page=min(self.page + 1, len(self.items) - 1))

    @button()
    async def skip(self, interaction: Interaction, btn: Button[Paginator]) -> None:
        await self.edit(interaction, page=len(self.items) - 1)

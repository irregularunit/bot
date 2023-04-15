"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from typing import TYPE_CHECKING, LiteralString

from discord import ButtonStyle, Guild, HTTPException, Interaction, Member, PartialEmoji
from discord.ui import Button, View, button

from models import EmbedBuilder, User

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("EmoteUnit", "EmoteView")


class EmoteUnit:
    """A unit of an emote.
    
    Parameters
    ----------
    name: `str`
        The name of the emote.
    id: `int`
        The ID of the emote.
    emote: `PartialEmoji`
        The emote.
    """
    __slots__: tuple[str, ...] = ("name", "id", "emote")

    def __init__(
        self,
        *,
        name: str,
        id: int,
        emote: PartialEmoji,
    ) -> None:
        self.name: str = name
        self.id: int = id
        self.emote: PartialEmoji = emote

    def __str__(self) -> str | None:
        return self.name


class EmoteView(View):
    """Simple embed and file paginator view
    
    Parameters
    ----------
    bot: `Bot`
        The bot instance.
    *items: `EmoteUnit`
        The emotes to paginate.

    Attributes
    ----------
    bot: `Bot`
        The bot instance.
    items: `tuple[EmoteUnit, ...]`
        The emotes to paginate.
    page: `int`
        The current page.
    """

    def __init__(self, bot: Bot, *items: EmoteUnit) -> None:
        super().__init__()
        self.bot: Bot = bot
        self.items: tuple[EmoteUnit, ...] = items
        self.page: int = 0

    def generate_page(self, unit: EmoteUnit) -> EmbedBuilder:
        """Generate the embed for the current page.

        Parameters
        ----------
        unit: `EmoteUnit`
            The emote unit.

        Returns
        -------
        `EmbedBuilder`
            The embed for the current page.
        """
        return (
            EmbedBuilder(description=f"`{unit.name}` `({unit.id})`")
            .set_image(url=unit.emote.url)
            .set_footer(text=f"Page {self.page + 1}/{len(self.items)}")
        )

    def next_page(self) -> None:
        """Go to the next page."""
        self.page = (self.page + 1) % len(self.items)

    def previous_page(self) -> None:
        """Go to the previous page."""
        self.page = (self.page - 1) % len(self.items)

    @button(label="<", style=ButtonStyle.secondary)
    async def back(self, interaction: Interaction[Bot], btn: Button[EmoteView]) -> None:
        self.previous_page()
        await interaction.response.edit_message(embed=self.generate_page(self.items[self.page]))

    @button(label=">", style=ButtonStyle.secondary)
    async def next(self, interaction: Interaction[Bot], btn: Button[EmoteView]) -> None:
        self.next_page()
        await interaction.response.edit_message(embed=self.generate_page(self.items[self.page]))

    async def send_to_ctx(self, ctx: Context) -> None:
        """Send the view to the context.

        Parameters
        ----------
        ctx: `Context`
            The context to send the view to.
        """
        self.add_item(StealEmoteButton(label="Steal", style=ButtonStyle.primary))
        await ctx.send(embed=self.generate_page(self.items[self.page]), view=self)


class StealEmoteButton(Button[EmoteView]):
    """Steal an emote button.

    Parameters
    ----------
    label: `str`
        The label of the button.
    style: `ButtonStyle`
        The style of the button.

    Attributes
    ----------
    steals: `dict[int, int]`
        A dictionary of user IDs and the number of times they've stolen an emote.
    """

    def __init__(self, label: str, style: ButtonStyle) -> None:
        super().__init__(label=label, style=style, emoji="🥷🏾", custom_id="steal")
        self.steals: dict[int, int] = {}

    async def read_emote(self, unit: EmoteUnit) -> bytes | None:
        """Read the emote from the URL.

        Parameters
        ----------
        unit: `EmoteUnit`
            The emote unit.

        Returns
        -------
        `bytes | None`
            The emote bytes, or `None` if the emote couldn't be read.
        """
        if self.view is None:
            raise AssertionError
        session: ClientSession = self.view.bot.session

        async with session.get(unit.emote.url + "?size=64") as resp:
            if resp.status == 200:
                return await resp.read()
            return None

    async def can_add_emoji(self, interaction: Interaction[Bot]) -> tuple[str, bool]:
        """Check if the user can add an emoji.

        Parameters
        ----------
        interaction: `Interaction[Bot]`
            The interaction.

        Returns
        -------
        `tuple[str, bool]`
            A tuple of the error message and whether the user can add an emoji.
        """
        if self.view is None:
            raise AssertionError
        bot: Bot = self.view.bot

        user_id: int = interaction.user.id
        if user_id not in bot.cached_users:
            user: User = await bot.manager.get_or_create_user(user_id)
            bot.cached_users[user_id] = user
        else:
            user = bot.cached_users[user_id]

        if user.emoji_server == 0:
            return "Looks like you haven't set your emoji server yet.", False

        emoji_server: Guild | None = bot.get_guild(user.emoji_server)
        if not emoji_server:
            return "Hey, I can't find your emoji server!", False

        guild_user: Member | None = emoji_server.get_member(user_id)
        if not guild_user:
            return "You're not in your emoji server!", False

        if not guild_user.guild_permissions.manage_emojis:
            return (
                "You don't have permission to add emojis this server...",
                False,
            )

        if not emoji_server.me.guild_permissions.manage_emojis:
            return (
                "I don't have permission to add emojis this server...",
                False,
            )

        if len(emoji_server.emojis) >= emoji_server.emoji_limit:
            return (
                "Your emoji server has reached the maximum amount of emojis...",
                False,
            )

        return "", True

    def updated_stealcounter(self, page: int) -> None:
        """Update the steal counter for the current page.

        Parameters
        ----------
        page: `int`
            The current page.
        """
        self.steals[page] = self.steals.get(page, 0) + 1

    def generate_embed(self, page: int) -> EmbedBuilder:
        """Generate the embed for the current page.

        Parameters
        ----------
        page: `int`
            The current page.

        Returns
        -------
        `EmbedBuilder`
            The embed builder.
        """
        if self.view is None:
            raise AssertionError
        items: tuple[EmoteUnit, ...] = self.view.items

        emoji: EmoteUnit = items[page - 1]
        tabs: LiteralString = '\t' * 6

        return (
            EmbedBuilder(description=f"`{emoji.name}` `({emoji.id})`")
            .set_image(url=emoji.emote.url)
            .set_footer(
                text=f"Page {page}/{len(items)}{tabs}{self.steals[page]}x {'steal' if self.steals[page] == 1 else 'steals'}"
            )
        )

    async def add_emoji(self, interaction: Interaction[Bot], unit: EmoteUnit) -> None:
        """Add the emote to the user's emoji server.

        Parameters
        ----------
        interaction: `Interaction[Bot]`
            The interaction.
        unit: `EmoteUnit`
            The emote unit.
        """
        if self.view is None:
            raise AssertionError
        bot: Bot = self.view.bot

        user_id: int = interaction.user.id
        user: User = bot.cached_users[user_id]
        emoji_server: Guild | None = bot.get_guild(user.emoji_server)
        if emoji_server is None:
            raise AssertionError

        emote: bytes | None = await self.read_emote(unit)
        if not emote:
            return await interaction.response.send_message("Couldn't read emote...", ephemeral=True)

        try:
            await emoji_server.create_custom_emoji(name=unit.name, image=emote)
        except HTTPException as exc:
            await interaction.response.send_message(f"Couldn't add emote: `{exc}`", ephemeral=True)
        else:
            self.updated_stealcounter(self.view.page)
            await interaction.response.edit_message(embed=self.generate_embed(self.view.page))

    async def callback(self, interaction: Interaction[Bot]) -> None:
        """Callback for the button.

        Parameters
        ----------
        interaction: `Interaction[Bot]`
            The interaction.
        """
        if self.view is None:
            raise AssertionError
        items: tuple[EmoteUnit, ...] = self.view.items

        reason, can_add = await self.can_add_emoji(interaction)
        if not can_add:
            return await interaction.response.send_message(reason, ephemeral=True)

        await self.add_emoji(interaction, items[self.view.page])

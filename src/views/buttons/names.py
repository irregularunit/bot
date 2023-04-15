"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from typing import Any

import discord

from models import EmbedBuilder

__all__: tuple[str, ...] = ("NameHistoryButton",)


class NameHistoryButton(discord.ui.Button):
    """A button that displays the user's name history.

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

    async def fetch_name_history(self, user_id: int) -> list[dict[str, Any]]:
        """Fetch the user's name history.

        Parameters
        ----------
        user_id: `int`
            The user's ID.

        Returns
        -------
        `list[dict[str, Any]]`
            The user's name history.
        """
        if self.view is None:
            raise AssertionError

        results = await self.view.bot.pool.fetch(
            """
            SELECT item_value, changed_at
            FROM item_history
            WHERE uuid = $1 AND item_type = 'name'
            ORDER BY changed_at DESC LIMIT 10
            """,
            user_id,
        )

        ret = []
        for result in results:
            ret.append(
                {
                    "item_value": result["item_value"],
                    "changed_at": result["changed_at"].strftime("%d %B %Y"),
                }
            )

        return ret

    async def callback(self, interaction: discord.Interaction) -> None:
        """The callback for the button.

        Parameters
        ----------
        interaction: `discord.Interaction`
            The interaction that triggered the button.
        """
        if self.view is None:
            raise AssertionError

        self.disabled = True
        await interaction.response.edit_message(view=self.view)

        name_history = await self.fetch_name_history(self.view.member.id)

        if not name_history:
            embed = EmbedBuilder(
                title="Name History",
                description="This user has not changed their username.",
            )
            await interaction.followup.send(embed=embed)
            return

        embed = EmbedBuilder(
            title="Name History",
            description="\n".join(
                f"**{name['item_value']}** - {name['changed_at']}" for name in name_history
            ),
        )

        await interaction.followup.send(embed=embed)
        await interaction.response.edit_message(view=self.view)

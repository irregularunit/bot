"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from typing import cast
from typing_extensions import override

from discord.abc import Messageable
from discord.ext.commands import MinimalHelpCommand

from models import EmbedBuilder

__all__: tuple[str, ...] = ("MinimalisticHelpCommand",)


class MinimalisticHelpCommand(MinimalHelpCommand):
    @override
    def __init__(self, **options) -> None:
        super().__init__(**options)

        self.verify_checks = False
        self.sort_commands = True
        self.no_category = "HelpSections"

    @override
    def get_opening_note(self) -> str:
        return ""

    @override
    def get_ending_note(self) -> str:
        return (
            "Type `{0}{1} <command>` for more info on a command.\n"
            "You can also type `{0}{1} <category>` for more info on a category."
        ).format(self.context.clean_prefix, self.invoked_with)
    
    @override
    async def send_pages(self) -> None:
        from utils.context import Context

        destination: Messageable = self.get_destination()

        if not self.context.bot.user:
            raise RuntimeError(
                "Bot hasn't been logged in yet. "
                "Shouldn't be possible to get here."
            )

        for page in self.paginator.pages:
            embed: EmbedBuilder = (
                EmbedBuilder.factory(
                    cast(Context, self.context),
                    description=page
                )
                .set_author(name="Help Menu", icon_url=self.context.bot.user.display_avatar)
            )
            await destination.send(embed=embed)

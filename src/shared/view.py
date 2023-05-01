# -*- coding: utf-8 -*-

from __future__ import annotations

import discord

__all__: tuple[str, ...] = ("SerenityView",)

UNKNOWN_INTERACTION = 10062


class SerenityView(discord.ui.View):
    async def on_error(
        self,
        interaction: discord.Interaction[discord.Client],
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        # Remove uselss noise from the logs.
        if isinstance(error, discord.NotFound):
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

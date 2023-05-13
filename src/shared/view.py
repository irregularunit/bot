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

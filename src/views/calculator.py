"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import simpleeval
from discord import ButtonStyle, Interaction
from discord.ui import Button, View, button

from models import EmbedBuilder

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("CalculatorView",)


sup = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "-": "⁻",
}
norm = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
}
operations = ["/", "*", "+", "-"]


class CalculatorView(View):
    """Simple calculator view"""

    def __init__(self, ctx: Context, *, embed: EmbedBuilder) -> None:
        super().__init__(timeout=60)
        self.ctx: Context = ctx
        self.embed: EmbedBuilder = embed

    async def interaction_check(self, interaction: Interaction[Bot]) -> bool:
        if interaction.user == self.ctx.author:
            return True

        await interaction.response.send_message(
            "This is not your calculator!", ephemeral=True
        )
        return False

    def find_description(self) -> str:
        """Find the description of the embed.

        Returns
        -------
        `str`
            The description of the embed.
        """
        return self.embed.description[8:-3]

    def edit_embed(self, label) -> str:
        content: str = self.find_description()
        if content == "0":
            return f"```yaml\n{label}```"

        try:
            if "Out" in content:
                return f"```yaml\n{label}```"
            if label == " ":
                return f"```yaml\n{content} ```"
            if content[-1] == "ˣ":
                return f"```yaml\n{content[:-1]}{sup[label]}```"
            if content[-1] in norm:
                return f"```yaml\n{content}{sup[label]}```"
            return f"```yaml\n{content}{label}```"
        except KeyError:
            return f"```yaml\n{content}```"

    @button(label="1", style=ButtonStyle.grey, row=0)
    async def first_button(self, interaction: Interaction, button: Button) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="2", style=ButtonStyle.grey, row=0)
    async def second_button(self, interaction: Interaction, button: Button) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="3", style=ButtonStyle.grey, row=0)
    async def third_button(self, interaction: Interaction, button: Button) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="*", style=ButtonStyle.green, row=0)
    async def fourth_button(self, interaction: Interaction, button: Button) -> None:
        self.embed.description = self.edit_embed(" * ")
        await interaction.response.edit_message(embed=self.embed)

    @button(label="√", style=ButtonStyle.green, row=0)
    async def fifth_button(self, interaction: Interaction, button: Button) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="4", style=ButtonStyle.grey, row=1)
    async def row_two_first_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="5", style=ButtonStyle.grey, row=1)
    async def row_two_second_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="6", style=ButtonStyle.grey, row=1)
    async def row_two_third_button(self, interaction: Interaction, button: Button):
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="-", style=ButtonStyle.green, row=1)
    async def row_two_fourth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(" - ")
        await interaction.response.edit_message(embed=self.embed)

    @button(label="ˣ", style=ButtonStyle.green, row=1)
    async def row_two_fifth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="7", style=ButtonStyle.grey, row=2)
    async def row_three_first_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="8", style=ButtonStyle.grey, row=2)
    async def row_three_second_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="9", style=ButtonStyle.grey, row=2)
    async def row_three_third_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="+", style=ButtonStyle.green, row=2)
    async def row_three_fourth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(" + ")
        await interaction.response.edit_message(embed=self.embed)

    @button(label="⌧", style=ButtonStyle.red, row=2)
    async def row_three_fifth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        content = self.find_description()
        display = f"```yaml\n{self.find_description()[:-1] if self.find_description() != '0' else '0'}```"

        if content[-1] == " " and content[-2] in operations:
            display = f"```yaml\n{content[:-3]}```"

        self.embed.description = display
        await interaction.response.edit_message(embed=self.embed)

    @button(label=".", style=ButtonStyle.grey, row=3)
    async def row_four_first_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="0", style=ButtonStyle.grey, row=3)
    async def row_four_second_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="=", style=ButtonStyle.grey, row=3)
    async def row_four_third_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        display = self.find_description()
        equation = "".join(k if k not in norm else f"**{norm[k]}" for k in display)
        pattern = re.compile(r"^√(\d+)")
        equation = pattern.sub("\\1 ** 0.5 ", equation)

        try:
            result = simpleeval.simple_eval(equation)
        except Exception:
            result = "Error! Something went wrong"
        self.embed.description = f"```yaml\nIn  << {display} \nOut >> {result}```"
        await interaction.response.edit_message(embed=self.embed)

    @button(label="/", style=ButtonStyle.green, row=3)
    async def row_four_fourth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(" / ")
        await interaction.response.edit_message(embed=self.embed)

    @button(label="Clear", style=ButtonStyle.red, row=3)
    async def row_four_fifth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = "```yaml\n0```"
        await interaction.response.edit_message(embed=self.embed)

    @button(label="(", style=ButtonStyle.blurple, row=4)
    async def row_five_first_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label=")", style=ButtonStyle.blurple, row=4)
    async def row_five_second_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(button.label)
        await interaction.response.edit_message(embed=self.embed)

    @button(label="Space", style=ButtonStyle.red, row=4)
    async def row_five_third_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        self.embed.description = self.edit_embed(" ")
        await interaction.response.edit_message(embed=self.embed)

    @button(label="Sci", style=ButtonStyle.red, row=4)
    async def row_five_fourth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        await interaction.response.send_message("Soon to come...", ephemeral=True)

    @button(label="Exit", style=ButtonStyle.red, row=4)
    async def row_five_fifth_button(
        self, interaction: Interaction, button: Button
    ) -> None:
        await interaction.response.edit_message()
        self.stop()

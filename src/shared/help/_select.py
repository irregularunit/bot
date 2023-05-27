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

from typing import Any, Dict, List, Tuple, TypeVar

from discord import Interaction, SelectOption
from discord.ext import commands
from discord.ui import Select

from .views._base import ABCHelpCommandView, HelpCommandView, HelpGroupCommandView, PluginHelp

CommandT = TypeVar("CommandT", bound=commands.Command[Any, Any, Any])


class CommandSelect(Select["ABCHelpCommandView"]):
    __slots__: Tuple[str, ...] = ("parent", "command_map")

    parent: ABCHelpCommandView
    command_map: Dict[str, commands.Command[Any, Any, Any]]

    def __init__(self, *, parent: ABCHelpCommandView, commands: Tuple[CommandT, ...]) -> None:
        self.parent = parent
        self.command_map = {str(command.qualified_name): command for command in commands if command}

        super().__init__(placeholder="Select a command...", options=self._options)

    @property
    def _options(self) -> List[SelectOption]:
        return [
            SelectOption(
                label=name,
                description=getattr(command, "brief", None) or "",
                value=name,
            )
            for name, command in self.command_map.items()
            if name.lower() not in ("help", "jishaku")
        ]

    async def callback(self, interaction: Interaction) -> None:
        selected_options = self.values

        if not selected_options:
            return

        command = self.command_map[selected_options[0]]

        if isinstance(command, commands.Group):
            view = HelpGroupCommandView(command, **self.parent.get_kwargs())
        else:
            view = HelpCommandView(command, **self.parent.get_kwargs())

        await interaction.response.edit_message(view=view, content=view.to_string())


class PluginSelect(Select["ABCHelpCommandView"]):
    __slots__: Tuple[str, ...] = (
        "parent",
        "plugin_map",
    )

    parent: ABCHelpCommandView
    plugin_map: Dict[str, commands.Cog]

    def __init__(self, *, parent: ABCHelpCommandView, plugins: Tuple[commands.Cog, ...]) -> None:
        self.parent = parent
        self.plugin_map = {str(plugin.qualified_name): plugin for plugin in plugins if plugin}

        super().__init__(placeholder="Select a plugin...", options=self._options)

    @property
    def _options(self) -> List[SelectOption]:
        return [
            SelectOption(
                label=name,
                description=plugin.__doc__,
                value=name,
            )
            for name, plugin in self.plugin_map.items()
            if name.lower() not in ("help", "jishaku")
        ]

    async def callback(self, interaction: Interaction) -> None:
        selected = self.values

        if not selected:
            return

        plugin = self.plugin_map[selected[0]]
        view = PluginHelp(plugin, **self.parent.get_kwargs())

        await interaction.response.edit_message(view=view, content=view.to_string())

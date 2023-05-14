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

from typing import Any, Dict, List, Sequence, Tuple

from discord import Interaction, SelectOption
from discord.ext import commands
from discord.ui import Select

from .views._base import ABCHelpCommandView, HelpCommandView, HelpGroupCommandView, PluginHelp


class CommandSelect(Select["ABCHelpCommandView"]):
    __slots__: Tuple[str, ...] = ("parent", "_commands", "_command_map")

    parent: ABCHelpCommandView
    _commands: Sequence[commands.Command[Any, Any, Any]]
    _command_map: Dict[str, commands.Command[Any, Any, Any]]

    def __init__(self, *, parent: ABCHelpCommandView, commands: Tuple[commands.Command[Any, Any, Any], ...]) -> None:
        self.parent = parent
        self._commands = commands
        self._command_map = {str(command.qualified_name): command for command in commands if command}

        super().__init__(placeholder="Select a command...", options=self._options)

    @property
    def _options(self) -> List[SelectOption]:
        return [
            SelectOption(
                label=str(command.qualified_name),
                description=getattr(command, "brief", None) or "",
                value=str(command.qualified_name),
            )
            for command in self._commands
            if command
        ]

    async def callback(self, interaction: Interaction) -> None:
        selected = self.values

        if not selected:
            return

        command = self._command_map[selected[0]]

        if isinstance(command, commands.Group):
            view = HelpGroupCommandView(command, **self.parent.get_kwargs())
        else:
            view = HelpCommandView(command, **self.parent.get_kwargs())

        await interaction.response.edit_message(view=view, embed=view.to_embed())


class PluginSelect(Select["ABCHelpCommandView"]):
    __slots__: Tuple[str, ...] = (
        "parent",
        "_plugins",
    )

    parent: ABCHelpCommandView
    _plugins: Sequence[commands.Cog]
    _plugin_map: Dict[str, commands.Cog]

    def __init__(self, *, parent: ABCHelpCommandView, plugins: Tuple[commands.Cog, ...]) -> None:
        self.parent = parent
        self._plugins = plugins
        self._plugin_map = {str(plugin.qualified_name): plugin for plugin in plugins if plugin}

        super().__init__(placeholder="Select a plugin...", options=self._options)

    @property
    def _options(self) -> List[SelectOption]:
        return [
            SelectOption(
                label=str(plugin.qualified_name),
                description=plugin.__doc__,
                value=str(plugin.qualified_name),
            )
            for plugin in self._plugins
            if plugin and not plugin.qualified_name.lower() == "jishaku"
        ]

    async def callback(self, interaction: Interaction) -> None:
        selected = self.values

        if not selected:
            return

        plugin = self._plugin_map[selected[0]]
        view = PluginHelp(plugin, **self.parent.get_kwargs())

        await interaction.response.edit_message(view=view, embed=view.to_embed())

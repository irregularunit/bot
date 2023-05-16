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

from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Tuple, TypeVar

from discord.ext import commands

from .views._base import HelpCommandView, HelpGroupCommandView, HelpView, PluginHelp

if TYPE_CHECKING:
    from src.models.discord import SerenityContext


__all__: Tuple[str, ...] = ("SerenityHelpCommand",)


CommandT = TypeVar("CommandT", bound=commands.Command[Any, Any, Any])


class SerenityHelpCommand(commands.HelpCommand):
    context: SerenityContext

    async def filter_mapping(
        self,
        mapping: Mapping[Optional[commands.Cog], List[CommandT]],
    ) -> Mapping[commands.Cog, List[CommandT]]:
        commands: List[CommandT] = [command for cog in mapping for command in mapping[cog]]
        await self.filter_commands(commands, sort=True)

        plugins: Dict[commands.Cog, List[CommandT]] = {}
        for command in commands:
            plugins.setdefault(command.cog, []).append(command)

        return plugins

    async def send_bot_help(
        self,
        mapping: Mapping[Optional[commands.Cog], List[CommandT]],
    ) -> None:
        filtered_mapping = await self.filter_mapping(mapping)
        view = HelpView(
            tuple(filtered_mapping.keys()),
            context=self.context,
        )
        await self.context.send(embed=view.to_embed(), view=view)

    async def send_cog_help(self, cog: commands.Cog, /) -> None:
        view = PluginHelp(cog, context=self.context)
        await self.context.send(embed=view.to_embed(), view=view)

    async def send_group_help(self, group: commands.Group[Any, Any, Any], /) -> None:
        view = HelpGroupCommandView(group, context=self.context)
        await self.context.send(embed=view.to_embed(), view=view)

    async def send_command_help(self, command: commands.Command[Any, Any, Any], /) -> None:
        view = HelpCommandView(command, context=self.context)
        await self.context.send(embed=view.to_embed(), view=view)

    def command_not_found(self, string: str, /) -> str:
        return f"Unable to locate `{string}` within the bot's commands."

    def subcommand_not_found(self, command: commands.Command[Any, Any, Any], string: str, /) -> str:
        return f"Command `{command.qualified_name}` has no subcommands matching `{string}`."

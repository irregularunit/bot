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

import abc
import itertools
from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional, ParamSpec, Tuple, TypeVar, Union

from discord import Interaction, Member, User
from discord.ext import commands

from src.shared import CommandExtras, SerenityConfig, SerenityView

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity


T = TypeVar("T")
P = ParamSpec("P")
Config = SerenityConfig.parse_obj({})


class PluginItem(NamedTuple):
    command: commands.Command[Any, Any, Any]
    extras: CommandExtras


class ABCHelpCommandView(SerenityView, abc.ABC):
    __slots__: Tuple[str, ...] = ("bot", "context", "author", "parent")

    bot: Serenity
    context: SerenityContext
    author: Union[Member, User]
    parent: Optional[ABCHelpCommandView]

    def __init__(
        self,
        *,
        context: SerenityContext,
        timeout: float = 60.0,
        parent: Optional[ABCHelpCommandView] = None,
    ) -> None:
        self.bot = context.bot
        self.context = context
        self.author = context.author
        self.parent = parent
        super().__init__(timeout=timeout)

    @abc.abstractmethod
    def to_string(self) -> str:
        ...

    def get_home(self) -> Optional[ABCHelpCommandView]:
        root = self

        while root.parent is not None:
            root = root.parent

        return None if root == self else root

    def get_kwargs(self) -> Dict[str, Any]:
        return {"context": self.context, "parent": self.parent or self, "timeout": self.timeout}

    def add_view_components(self) -> None:
        from .._buttons import DisableButton, ToStart

        if self.parent is not None:
            if home := self.get_home():
                self.add_item(ToStart(parent=home))

        self.add_item(DisableButton(parent=self))

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        check = self.author == interaction.user

        if not check:
            await interaction.response.send_message("You are not allowed to use this menu.", ephemeral=True)

        return check


class HelpGroupCommandView(ABCHelpCommandView):
    __slots__: Tuple[str, ...] = ("group", "group_name")

    group: commands.Group[Any, Any, Any]

    def __init__(self, group: commands.Group[Any, Any, Any], **kwargs: Any) -> None:
        from .._select import CommandSelect

        self.group = group
        self.group_name = group.qualified_name

        group_commands = list(group.commands)

        for command in group_commands:
            if command.hidden:
                group_commands.remove(command)

            if isinstance(command, commands.Group):
                group_commands.extend(command.commands)

        super().__init__(**kwargs)

        for chunk in itertools.zip_longest(*[iter(group_commands)] * 20):
            self.add_item(CommandSelect(parent=self, commands=chunk))

        super().add_view_components()

    def to_string(self) -> str:
        ...


class HelpCommandView(ABCHelpCommandView):
    __slots__: Tuple[str, ...] = ("command", "extras")

    command: commands.Command[Any, Any, Any]
    extras: CommandExtras

    def __init__(self, command: commands.Command[Any, Any, Any], **kwargs: Any) -> None:
        self.command = command
        self.extras: CommandExtras = getattr(
            command,
            "extras",
            CommandExtras(description="No description provided.", example="No example provided.", options=()),
        )

        super().__init__(**kwargs)
        super().add_view_components()

    def to_string(self) -> str:
        ...


class HelpView(ABCHelpCommandView):
    __slots__: Tuple[str, ...] = ()

    def __init__(self, plugin: Tuple[commands.Cog], **kwargs: Any) -> None:
        from .._select import PluginSelect

        super().__init__(**kwargs)
        self.add_item(PluginSelect(parent=self, plugins=plugin))

        super().add_view_components()

    def to_string(self) -> str:
        ...


class PluginHelp(ABCHelpCommandView):
    __slots__: Tuple[str, ...] = ("plugin",)

    plugin: commands.Cog

    def __init__(self, plugin: commands.Cog, **kwargs: Any) -> None:
        from .._select import CommandSelect

        self.plugin = plugin

        super().__init__(**kwargs)

        # FIXME: STOOPID
        for chunk in itertools.zip_longest(*[iter(plugin.get_commands())] * 20):
            self.add_item(CommandSelect(parent=self, commands=chunk))

        super().add_view_components()

    def to_string(self) -> str:
        ...

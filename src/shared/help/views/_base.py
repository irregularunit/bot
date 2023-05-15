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

from src.plugins.meta.utils import GITHUB_URL, LICENSE
from src.shared import CommandExtras, SerenityConfig, SerenityEmbed, SerenityView

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
    def to_embed(self) -> SerenityEmbed:
        ...

    def get_home(self) -> Optional[ABCHelpCommandView]:
        root = self

        while root.parent is not None:
            root = root.parent

        if root == self:
            return None

        return root

    def get_kwargs(self) -> Dict[str, Any]:
        return {"context": self.context, "parent": self.parent or self, "timeout": self.timeout}

    def _add_view_components(self) -> None:
        from .._buttons import DeleteView, ToStart

        if self.parent is not None:
            home = self.get_home()

            if home:
                self.add_item(ToStart(parent=home))

        self.add_item(DeleteView(parent=self))

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        check = self.author == interaction.user

        if check is False:
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

        for chunk in itertools.zip_longest(*[iter(group_commands)] * 20):
            super().__init__(**kwargs)
            self.add_item(CommandSelect(parent=self, commands=chunk))

        super()._add_view_components()

    def to_embed(self) -> SerenityEmbed:
        embed = SerenityEmbed(title=f"Help for {self.group.qualified_name}")
        embed.add_field(
            name="Description",
            value=self.group.description or "No description provided.",
            inline=False,
        )
        embed.add_field(
            name="Section",
            value=self.group.cog_name or "No section found.",
            inline=False,
        )

        if self.group.commands:
            embed.add_field(
                name="Subcommands",
                value="\n".join(f"`{command.name}`" for command in self.group.commands if not command.hidden),
                inline=False,
            )

        return embed


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
        super()._add_view_components()

    def to_embed(self) -> SerenityEmbed:
        embed = SerenityEmbed(title=f"Help for {self.command.qualified_name}")

        example = self.extras["example"].format(
            prefix=self.context.clean_prefix,
            command=self.command.qualified_name,
        )

        embed.add_field(
            name="Description",
            value=self.extras["description"],
            inline=False,
        )

        if self.extras["options"]:
            embed.add_field(
                name="Arguments",
                value="\n".join(f"`{option}` - {description}" for option, description in self.extras["options"]),
                inline=False,
            )

        embed.add_field(
            name="Usage",
            value=(
                f"`{self.context.clean_prefix}{self.command.qualified_name} {self.command.signature}`"
                + (f"\n\n**Example**\n`{example}`" if example else "No example provided.")
            ),
            inline=False,
        )

        if self.command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in self.command.aliases),
                inline=False,
            )

        return embed


class HelpView(ABCHelpCommandView):
    __slots__: Tuple[str, ...] = ()

    def __init__(self, plugin: Tuple[commands.Cog], **kwargs: Any) -> None:
        from .._select import PluginSelect

        super().__init__(**kwargs)
        self.add_item(PluginSelect(parent=self, plugins=plugin))

        super()._add_view_components()

    def to_embed(self) -> SerenityEmbed:
        if self.bot.user is None:
            raise RuntimeError("Unable to initialize help menu. Due to bot not being ready.")

        embed = SerenityEmbed(
            description=(
                f"""
                [Github]({GITHUB_URL}) | [License]({LICENSE}) | [Invite]({Config.invite})

                **{self.context.me.name} Help Menu**
                Use the select menu to navigate through the help menu.
                > `s? help <command>` to get more information about a command.
                > `s? help <category>` to get more information about a category.

                **About ME**
                I am Serenity, a custom bot solution created by `@lexicalunit` for the exclusive 
                use of the `SerenityOS` server. Written in Python using the `discord.py` library.

                **Support**
                If you require assistance, please feel free to join my support server [here](https://discord.gg/U8ns9TZVxb).
                """
            )
        )
        embed.set_author(name=self.context.me, icon_url=self.context.me.display_avatar)

        return embed


class PluginHelp(ABCHelpCommandView):
    __slots__: Tuple[str, ...] = ("plugin",)

    plugin: commands.Cog

    def __init__(self, plugin: commands.Cog, **kwargs: Any) -> None:
        from .._select import CommandSelect

        self.plugin = plugin
        super().__init__(**kwargs)

        for chunk in itertools.zip_longest(*[iter(plugin.get_commands())] * 20):
            super().__init__(**kwargs)
            self.add_item(CommandSelect(parent=self, commands=chunk))

        super()._add_view_components()

    def to_embed(self) -> SerenityEmbed:
        plugin = self.plugin

        embed = SerenityEmbed(
            title=f"Help for {plugin.qualified_name}",
            description=plugin.description or "No description provided.",
        )
        embed.add_field(
            name="List of Commands",
            value=(", ".join(f"`{command.name}`" for command in plugin.get_commands() if not command.hidden)),
            inline=False,
        )

        return embed

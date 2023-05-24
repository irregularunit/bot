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
import textwrap
from io import StringIO
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

    def _add_view_components(self) -> None:
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

        # FIXME: STUPID
        for chunk in itertools.zip_longest(*[iter(group_commands)] * 20):
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
            formatted_commands = "\n".join(f"`{command.name}`" for command in self.group.commands if not command.hidden)

            embed.add_field(
                name="Subcommands",
                value=formatted_commands,
                inline=False,
            )

        return embed

    def to_string(self) -> str:
        buffered_io = StringIO()

        start, end = "```prolog", "```"
        header = f"\n=== Help for '{self.group.qualified_name}' ===\n\n"
        description = f"Description:\n・ '{self.group.description or 'No description provided.'}'\n\n"

        buffered_io.write(start)
        buffered_io.write(header)
        buffered_io.write(description)

        for command in self.group.commands:
            if command.hidden:
                continue

            buffered_io.write(f"{command.name:10} :: {command.description or 'No description provided.'}\n")

        buffered_io.write(end)

        return buffered_io.getvalue()


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
        options_found = self.extras["options"]
        example_command = self.extras["example"]
        formatted_example = example_command.format(
            prefix=self.context.clean_prefix,
            command=self.command.qualified_name,
        )

        embed.add_field(
            name="Description",
            value=self.extras["description"],
            inline=False,
        )

        if options_found:
            embed.add_field(
                name="Arguments",
                value="\n".join(option.markup() for option in options_found),
                inline=False,
            )

        example = f"\n\n**Example**\n`{formatted_example}`" if example_command else "No example provided."

        embed.add_field(
            name="Usage",
            value=f"`{self.context.clean_prefix}{self.command.qualified_name} {self.command.signature}`{example}",
            inline=False,
        )

        if self.command.aliases:
            formatted_aliases = ", ".join(f"`{alias}`" for alias in self.command.aliases)

            embed.add_field(
                name="Aliases",
                value=formatted_aliases,
                inline=False,
            )

        return embed

    def to_string(self) -> str:
        buffered_io = StringIO()

        start, end = "```prolog", "```"
        options_found = self.extras["options"]
        header = f"\n=== Help for '{self.command.qualified_name}' ===\n\n"
        description = f"Description:\n・ '{self.extras['description']}'\n\n"

        buffered_io.write(start)
        buffered_io.write(header)
        buffered_io.write(description)

        if options_found:
            buffered_io.write("\nArguments:\n")
            for option in options_found:
                buffered_io.write(f"{option.markup()}")

        example_command = self.extras["example"]
        formatted_example = example_command.format(
            prefix=self.context.clean_prefix,
            command=self.command.qualified_name,
        )

        example = f"\n\nExample:\n・ '{formatted_example}'" if example_command else "'No example provided.'"

        buffered_io.write(
            f"\nUsage:\n・ '{self.context.clean_prefix}{self.command.qualified_name} {self.command.signature}'"
            + example
            + "\n"
        )

        if self.command.aliases:
            formatted_aliases = "\n".join(f"・ '{alias}'" for alias in self.command.aliases)

            buffered_io.write(f"\nAliases:\n{formatted_aliases}")

        buffered_io.write(end)

        return buffered_io.getvalue()


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

                **About Me**
                I am Serenity, a custom bot solution created by `@lexicalunit` for the exclusive 
                use of the `SerenityOS` server. Written in Python using the `discord.py` library.

                **Support**
                If you require assistance, please feel free to join my support server [here](https://discord.gg/U8ns9TZVxb).
                """
            )
        )

        embed.set_author(name=self.context.me, icon_url=self.context.me.display_avatar)

        return embed

    def to_string(self) -> str:
        fmt = """
        ```prolog
        ╔═══════════════════════════════════════════════════╗
        ║                Serenity Help Menu                 ║
        ║                                                   ║
        ║ use the select menu to navigate through the help  ║
        ║ menu.                                             ║
        ║                                                   ║
        ║ > `s? help <command>` to get more information     ║
        ║   about a command.                                ║
        ║ > `s? help <category>` to get more information    ║
        ║   about a category.                               ║
        ╚===================================================╝
        ```
        """

        return textwrap.dedent(fmt)


class PluginHelp(ABCHelpCommandView):
    __slots__: Tuple[str, ...] = ("plugin",)

    plugin: commands.Cog

    def __init__(self, plugin: commands.Cog, **kwargs: Any) -> None:
        from .._select import CommandSelect

        self.plugin = plugin

        super().__init__(**kwargs)

        # FIXME: STUPID
        for chunk in itertools.zip_longest(*[iter(plugin.get_commands())] * 20):
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
            value=("\n".join(f"・ '{command.name}'" for command in plugin.get_commands() if not command.hidden)),
            inline=False,
        )

        return embed

    def to_string(self) -> str:
        plugin = self.plugin

        buffered_io = StringIO()

        start, end = "```prolog", "```"
        header = f"\n=== Help for '{plugin.qualified_name}' ===\n\n"
        description = f"Description:\n・ {plugin.description or 'No description provided.'}\n"

        buffered_io.write(start)
        buffered_io.write(header)
        buffered_io.write(description)

        buffered_io.write("\nList of Commands:\n")
        for command in plugin.get_commands():
            if command.hidden:
                continue

            buffered_io.write(f"・ '{command.name}'\n")

        buffered_io.write(end)

        return buffered_io.getvalue()

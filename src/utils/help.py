"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from io import StringIO
from typing import Any, Sequence, cast

from discord.abc import Messageable
from discord.ext.commands import Command, Group, MinimalHelpCommand
from typing_extensions import override

from models import EmbedBuilder

__all__: tuple[str, ...] = ("MinimalisticHelpCommand",)


class MinimalisticHelpCommand(MinimalHelpCommand):
    """A minimalistic help command for the bot.

    Attributes
    ----------
    `verify_checks`
        Whether to verify checks.
    `sort_commands`
        Whether to sort commands.
    `no_category`
        The name of the no category.

    # See discord.ext.commands.MinimalHelpCommand for more attributes
    """

    @override
    def __init__(self, **options) -> None:
        super().__init__(**options)

        self.verify_checks = False
        self.sort_commands = True
        self.no_category = "\N{COMPASS} HelpSections"

    @override
    def get_command_signature(self, command: Command[Any, ..., Any], /) -> str:
        """Return a signature portion from the given command.

        Parameters
        ----------
        command: :class:`Command`
            The command to get the signature of.

        Returns
        -------
        `str`
            The signature of the command.
        """
        return (
            f"{self.context.clean_prefix}{command.qualified_name} "
            f"{command.signature.replace('<', '{').replace('>', '}')}"
        )

    @override
    def get_opening_note(self) -> str:
        """Return the help command's opening note. This is mainly useful to override for i18n purposes.

        The default implementation has been overridden to return an empty string.

        Returns
        -------
        `str`
            The help command opening note.
        """
        return (
            f"Type `{self.context.clean_prefix}{self.invoked_with} {'{command}'}` for more info on a command.\n"
            f"You can also type `{self.context.clean_prefix}{self.invoked_with} {'{category}'}` for more info on a category."
        )

    @override
    def get_ending_note(self) -> str:
        """Return the help command's ending note. This is mainly useful to override for i18n purposes.

        The default implementation does nothing.

        Returns
        -------
        `str`
            The help command ending note.
        """
        return ""

    @override
    async def send_pages(self) -> None:
        """A helper method to send the help pages to the destination."""

        # Importing here to avoid circular imports
        from utils.context import Context

        destination: Messageable = self.get_destination()

        if not self.context.bot.user:
            raise RuntimeError("Bot hasn't been logged in yet. Shouldn't be possible to get here.")

        for page in self.paginator.pages:
            if "brackets" not in page:
                embed: EmbedBuilder = EmbedBuilder.factory(
                    cast(Context, self.context), description=page
                ).set_author(name="Help Menu", icon_url=self.context.bot.user.display_avatar)
                await destination.send(embed=embed)
            else:
                await destination.send(page)

    @override
    def add_bot_commands_formatting(
        self, commands: Sequence[Command[Any, ..., Any]], heading: str, /
    ) -> None:
        """Adds the minified bot heading with commands to the output.

        The formatting should be added to the :attr:`paginator`.

        The default implementation is a bold underline heading followed
        by commands separated by an EN SPACE (U+2002) in the next line.

        Parameters
        ----------
        commands: `Sequence[Command]`
            A list of commands that belong to the heading.
        heading: `:class:str`
            The heading to add to the line.
        """
        if commands:
            # U+2002 Middle Dot, and `
            cog = commands[0].cog
            joined: str = '\u2002'.join(f'`{c.name}`' for c in commands)

            if getattr(cog, "emoji", None):
                if not isinstance(cog.emoji, str):
                    raise TypeError(f"Expected emoji to be a str, got {type(cog.emoji)} instead.")

                emote: str = cog.emoji
                heading = f"{emote} __**{heading}**__"
            else:
                heading = f"__**{heading}**__"

            self.paginator.add_line(heading)
            self.paginator.add_line(joined)

    @override
    def add_command_formatting(self, command: Command[Any, ..., Any], /) -> None:
        """A utility function to format commands and groups.

        Parameters
        ----------
        command: :class:`Command`
            The command to format.
        """
        subcommands = (
            '\n'.join(self.get_command_signature(c) for c in command.commands)
            if isinstance(command, Group)
            else ''
        )
        aliases = ' , '.join(command.aliases) or "Nil"
        description = command.help or "Nil"
        examples = command.brief or ("Nil",)

        example_builder = StringIO()
        for index, example in enumerate(examples, start=1):
            prefix = self.context.clean_prefix

            if index == 1:
                example_builder.write(f"{prefix}{example}")
            else:
                example_builder.write(f"\n{prefix}{example}")

        related_commands = ("Nil",)  # type: ignore

        help_message = f"""```md
            {self.get_command_signature(command)}
            ``````md
            # Aliases
            {aliases}
            # Description
            {description}
            # Example Command(s)
            {example_builder.getvalue()}
            # Related Commands
            {', '.join(related_commands)}
            {'# Subcommands' if isinstance(command, Group) else ''}
            {subcommands}
            ``````md
            > Remove brackets when typing commands
            > [] = Optional arguments
            > {{}} = Required arguments
            ```
        """

        help_message = help_message.replace(" " * 12, "")
        self.paginator.add_line(help_message)

    @override
    async def send_group_help(self, group: Group[Any, ..., Any], /) -> None:
        self.add_command_formatting(group)
        await self.send_pages()

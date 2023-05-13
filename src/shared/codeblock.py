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

from enum import Enum
from typing import TYPE_CHECKING, AnyStr, Optional

if TYPE_CHECKING:
    from src.models.discord import SerenityContext

__all__: tuple[str, ...] = ("Codeblock",)


class State(Enum):
    initial_whitespace = 0
    opening_backticks = 1
    first_line = 2
    content = 3


class Codeblock:
    """A class to represent a discord codeblock.

    Attributes
    ----------
    content: `str`
        The content of the codeblock.
    language: `Optional[str]`
        The language of the codeblock.
    """

    content: str
    language: Optional[str]
    inline: bool = False

    def __init__(self, content: AnyStr, *, language: Optional[str] = None, inline: bool = False) -> None:
        if isinstance(content, str):
            self.content = content
        else:
            try:
                self.content = content.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Content must be a string or bytes-like object.")

        self.language = language
        self.inline = inline

    @staticmethod
    def _is_backtick(char: str) -> bool:
        return char == "`"

    @staticmethod
    def _would_close(argument: str, cursor: int, backticks: int) -> bool:
        """Check if a codeblock would be closed.

        Parameters:
        -----------
        argument : `str`
            The string to check.
        cursor : `int`
            The current cursor position.
        backticks : `int`
            The number of backticks used to open the codeblock.

        Returns:
        --------
        `bool`
            True if the codeblock would be closed, False otherwise.
        """
        return argument[cursor:].startswith("`" * backticks) and (
            cursor + backticks == len(argument) or argument[cursor + backticks].isspace()
        )

    @staticmethod
    def _parse_codeblock(argument: str, start: int, end: int, backticks: int) -> tuple[str, str]:
        """Parse a codeblock and return its language and content.

        Parameters:
        -----------
        argument : `str`
            The string to parse.
        start : `int`
            The start of the codeblock.
        end : `int`
            The end of the codeblock.
        backticks : `int`
            The number of backticks used to open the codeblock.

        Returns:
        --------
        `tuple[str, str]`
            The language and content of the codeblock.
        """

        language = argument[start + backticks : end].strip()
        content_start = argument.find("\n", end) + 1
        content_end = argument.rfind("`" * backticks, content_start, -1)
        content = argument[content_start:content_end]
        return language, content

    @classmethod
    async def convert(cls, ctx: SerenityContext, argument: str) -> Codeblock:
        """Convert a string to a codeblock.

        Parameters:
        -----------
        ctx : `SerenityContext`
            The invocation context.
        argument : `str`
            The string to convert.

        Returns:
        --------
        `Codeblock`
            The converted codeblock.

        Raises:
        -------
        `ValueError`
            If the codeblock is invalid.
        """

        closing_backticks = ""  # type: ignore
        backticks = 0
        cursor = 0
        state = State.initial_whitespace

        while cursor < len(argument):
            current = argument[cursor]

            if state is State.initial_whitespace:
                if cls._is_backtick(current):
                    state = State.opening_backticks
                    backticks = 1
                elif not current.isspace():
                    raise ValueError("Code blocks must begin with backticks.")

                # FIXME: Needs proper handling
                if not argument.endswith("```"):
                    argument += "```"

            elif state is State.opening_backticks:
                if cls._is_backtick(current):
                    backticks += 1
                else:
                    state = State.first_line
                    first_line_start = cursor
                    closing_backticks = "`" * backticks  # type: ignore

            elif current == "\n":
                if state is State.first_line:
                    state = State.content
                elif state is State.content and cls._would_close(argument, cursor, backticks):
                    language, content = cls._parse_codeblock(argument, first_line_start, cursor, backticks)  # type: ignore
                    return Codeblock(content, language=language)

            cursor += 1

        if state is State.content and cls._would_close(argument, cursor, backticks):
            language, content = cls._parse_codeblock(argument, first_line_start, cursor, backticks)  # type: ignore
            return Codeblock(content, language=language)

        return Codeblock(argument)

    def __str__(self) -> str:
        return f"{self.language or ''}\n{self.content}"

    def markup(self) -> str:
        if self.inline:
            return f"`{self.content}`"
        else:
            return f"```{self.language or ''}\n{self.content}\n```"

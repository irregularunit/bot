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

from typing import NamedTuple, Tuple, TypedDict, Union

import discord
from discord.ext import commands

from src.models.discord.converter import MaybeMemberConverter

__all__: tuple[str, ...] = (
    "CommandOption",
    "CommandExtras",
    "DefaultExample",
    "MaybeMember",
    "MaybeMemberParam",
)


MaybeMember = Union[discord.User, MaybeMemberConverter]
MaybeMemberParam = commands.param(
    converter=MaybeMember,
    displayed_default="author",
    default=None,
)
DefaultExample: str = "{1}{2} {3}"


class CommandOption(NamedTuple):
    option: str
    description: str

    def __str__(self) -> str:
        return f"・`{self.option}` - {self.description}\n"

    def markup(self) -> str:
        return str(self)


class CommandExtras(TypedDict):
    description: str
    options: Tuple[CommandOption, ...]
    example: str

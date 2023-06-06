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

from typing import Any, NamedTuple, Tuple, TypedDict, Union

import discord
from discord.ext import commands

from src.models.discord.converter import MaybeMemberConverter

__all__: tuple[str, ...] = (
    "CommandOption",
    "CommandExtras",
    "MaybeMember",
    "DefaultArg",
    "MaybeMemberParam",
)


class attrgetter:
    __slots__ = ('_attrs', '_call')

    def __init__(self, attr: Any, *attrs: str) -> None:
        if not attrs:
            if not isinstance(attr, str):
                raise TypeError('attribute name must be a string')
            self._attrs = (attr,)
            names = attr.split('.')

            def func(obj: Any) -> Any:
                for name in names:
                    obj = getattr(obj, name)
                return obj

            self._call = func
        else:
            self._attrs = (attr,) + attrs
            getters = tuple(map(attrgetter, self._attrs))

            def func(obj: Any) -> Any:
                return tuple(getter(obj) for getter in getters)

            self._call = func

    def __call__(self, obj: Any) -> Any:
        return self._call(obj)

    def __repr__(self) -> str:
        return f"{self.__class__.__module__}." f"{self.__class__.__qualname__}(" f"{', '.join(map(repr, self._attrs))})"

    def __reduce__(self) -> tuple[Any, ...]:
        return self.__class__, self._attrs


MaybeMember = Union[discord.User, MaybeMemberConverter]
MaybeMemberParam = commands.param(
    converter=MaybeMember,
    displayed_default="<author>",
    default=attrgetter("author"),
)
DefaultArg = "{prefix}{command}"


class CommandOption(NamedTuple):
    option: str
    description: str

    def __str__(self) -> str:
        return f"・ '{self.option}' - '{self.description}'\n"

    def markup(self) -> str:
        return str(self)


class CommandExtras(TypedDict):
    description: str
    options: Tuple[CommandOption, ...]
    example: str

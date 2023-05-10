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

from typing import TYPE_CHECKING, Any, Callable, Type, TypeVar
from uuid import uuid4

from discord.app_commands import Command as AppCommand
from discord.ext import commands
from typing_extensions import override

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Plugin", "for_command_callbacks")


T = TypeVar("T")
CogT_co = TypeVar("CogT_co", covariant=True, bound=commands.Cog)
CommandT = AppCommand | commands.Command  # type: ignore


class Plugin(commands.Cog):
    """Base class for all plugins."""

    @override
    async def cog_check(self, ctx: SerenityContext) -> bool:  # type: ignore
        return self.serenity.is_plugin_enabled(self)

    def __init__(self, serinity: Serenity, *args: Any, **kwargs: Any) -> None:
        self.serenity = serinity
        self.id = uuid4()
        next_in_method_resolution_order = next(iter(self.__class__.__mro__))

        if issubclass(next_in_method_resolution_order, self.__class__):
            kwargs["bot"] = serinity

        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<Plugin id={self.id!r} name={self.__class__.__name__!r} at {hex(id(self))}>"

    def __str__(self) -> str:
        return self.__class__.__name__


def for_command_callbacks(
    decorator: Callable[[Any], Callable[[Type[T]], Type[T]]]
) -> Callable[[Type[T]], Type[T]]:
    """Decorator for command callbacks.

    Parameters
    ----------
    decorator : `Callable[[Any], Callable[[Type[T]], Type[T]]]`
        The decorator to decorate the command callbacks with.

    Returns
    -------
    `Callable[[Type[T]], Type[T]]`
        The decorated command callback.
    """

    def inner(cls: Type[T]) -> Type[T]:
        """The inner function for the command callback decorator.

        Parameters
        ----------
        cls : `Type[T]`
            The class to decorate to map callbacks to.

        Returns
        -------
        `Type[T]`
            The decorated class.
        """
        for attr in dir(cls):
            method = getattr(cls, attr)
            if isinstance(method, CommandT):
                setattr(cls, attr, decorator(method))  # type: ignore

        return cls

    return inner

# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from discord.ext import commands

if TYPE_CHECKING:
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Plugin",)


class Plugin(commands.Cog):
    """Base class for all plugins."""

    def __init__(self, serinity: Serenity, *args: Any, **kwargs: Any) -> None:
        self.serenity = serinity
        self.id = uuid4()
        self.logger = serinity.logger.getChild(self.__class__.__name__)

        next_in_method_resolution_order = next(iter(self.__class__.__mro__))

        if issubclass(next_in_method_resolution_order, self.__class__):
            kwargs["bot"] = serinity

        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<Plugin id={self.id!r} name={self.__class__.__name__!r} at {hex(id(self))}>"

    def __str__(self) -> str:
        return self.__class__.__name__

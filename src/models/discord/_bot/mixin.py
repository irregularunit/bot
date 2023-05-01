# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import os
import pathlib
import re
from typing import Any, Callable, Generator, ParamSpec, TypeVar

from discord.utils import copy_doc

__all__: tuple[str, ...] = ("SerenityMixin",)

P = ParamSpec("P")
T = TypeVar("T")


class SerenityMixin:
    """A mixin for the Serenity bot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @staticmethod
    def compile_prefixes(prefixes: list[str], /) -> re.Pattern[str]:
        """Compile a list of prefixes into a regular expression.

        Parameters
        ----------
        guild : `int`
            The ID of the guild.
        prefixes : `list[str]`
            The prefixes to compile.

        Returns
        -------
        `re.Pattern[str]`
            The compiled regular expression.
        """
        return re.compile(
            r"|".join(re.escape(prefix) + r"\s*" for prefix in prefixes if prefix),
            re.IGNORECASE,
        )

    @staticmethod
    @copy_doc(asyncio.to_thread)
    async def to_thread(func: Callable[P, T], /, *args: Any, **kwargs: Any) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def strchunk(item: str, *, size: int = 2000) -> Generator[str, None, None]:
        """Split a string into chunks of a given size.

        Parameters
        ----------
        item : `str`
            The string to split.
        size : `int`
            The maximum size of each chunk.

        Yields
        ------
        `str`
            The chunks of the string.
        """
        for i in range(0, len(item), size):
            yield item[i : i + size]

    @staticmethod
    def walk_plugins() -> Generator[str, None, None]:
        """Walk the plugins directory and yield the names of the plugins.

        Yields
        ------
        `str`
            The fully qualified name of the plugin.
        """
        plugins = [
            file for file in os.listdir("src/plugins") if not file.startswith("_")
        ]
        for plugin in plugins:
            yield f"src.plugins.{plugin[:-3] if plugin.endswith('.py') else plugin}"

    @staticmethod
    def walk_schemas() -> Generator[pathlib.Path, None, None]:
        """Walk the migrations directory and yield the names of the schemas.

        Yields
        ------
        `pathlib.Path`
            The path to the schema.^
        """
        schemas = [
            file for file in os.listdir("src/migrations") if not file.startswith("_")
        ]

        def _sort_key(schema: str) -> int:
            return int(schema.split("_")[0])

        for schema in sorted(schemas, key=_sort_key):
            yield pathlib.Path(f"src/migrations/{schema}")

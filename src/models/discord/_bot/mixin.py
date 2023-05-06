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

import asyncio
import os
import pathlib
import re
from itertools import islice
from typing import TYPE_CHECKING, Any, Callable, Generator, ParamSpec, TypeVar

from discord.utils import copy_doc

if TYPE_CHECKING:
    from src.shared import Plugin

__all__: tuple[str, ...] = ("SerenityMixin",)

P = ParamSpec("P")
T = TypeVar("T")


class SerenityMixin:
    """A mixin for the Serenity bot."""

    _plugins: dict[str, bool] = {}

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
        it = iter(item)
        while True:
            chunk = "".join(islice(it, size))
            if not chunk:
                return
            yield chunk

    @staticmethod
    def chunk(*items: T, size: int = 1) -> Generator[tuple[T], None, None]:
        """Splits a iterable into chunks of a given size.

        Parameters
        ----------
        items : `list[T]`
            The list to split.
        size : `int`
            The maximum size of each chunk.

        Yields
        ------
        `list[T]`
            The chunks of the list.
        """
        for i in range(0, len(items), size):
            yield items[i : i + size]

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
            SerenityMixin._plugins[plugin] = True

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

    def is_plugin_enabled(self, plugin: Plugin, /) -> bool:
        """Check if a plugin is enabled.

        Parameters
        ----------
        plugin : `Plugin`
            The plugin to check.

        Returns
        -------
        `bool`
            Whether the plugin is enabled.
        """
        return SerenityMixin._plugins.get(str(plugin).lower(), False)

    def enable_plugin(self, plugin: Plugin, /) -> None:
        """Enable a plugin.

        Parameters
        ----------
        plugin : `Plugin`
            The plugin to enable.
        """
        SerenityMixin._plugins[str(plugin).lower()] = True

    def disable_plugin(self, plugin: Plugin, /) -> None:
        """Disable a plugin.

        Parameters
        ----------
        plugin : `Plugin`
            The plugin to disable.
        """
        SerenityMixin._plugins[str(plugin).lower()] = False

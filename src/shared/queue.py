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

from asyncio import AbstractEventLoop, Queue, QueueEmpty, get_event_loop
from typing import Optional, Tuple, TypeVar

__all__: Tuple[str, ...] = ("SerenityQueue",)

T = TypeVar("T")


class SerenityQueue(Queue[T]):
    __loop: AbstractEventLoop

    def __init__(self, maxsize: int = 0, loop: Optional[AbstractEventLoop] = None) -> None:
        super().__init__(maxsize=maxsize)

        if loop is None:
            self.__loop = get_event_loop()
        else:
            self.__loop = loop

    @property
    def loop(self) -> AbstractEventLoop:
        return self.__loop

    @property
    def size(self) -> int:
        return self.qsize()

    async def insert_many(self, *items: T) -> None:
        for item in items:
            await self.put(item)

    async def get_many(self, count: int) -> list[T]:
        items: list[T] = []

        for _ in range(count):
            try:
                items.append(await self.get())
            except QueueEmpty:
                break

        return items

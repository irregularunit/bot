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

from asyncio import Queue, QueueEmpty
from datetime import datetime
from io import BytesIO
from typing import Generic, NamedTuple, TypeVar

import discord
from magic import from_buffer

from src.imaging import AvatarPointer

__all__: tuple[str, ...] = (
    "AssetEntitiy",
    "StoreQueue",
    "PresenceEntry",
    "PRESENCE_STATUSES",
    "type_of",
)


PRESENCE_STATUSES = {
    discord.Status.online: "Online",
    discord.Status.offline: "Offline",
    discord.Status.idle: "Idle",
    discord.Status.dnd: "Do Not Disturb",
}

T = TypeVar("T")


class AssetEntitiy(NamedTuple):
    """A named tuple for items in the send queue."""

    id: int
    image: bytes
    mime_type: str

    def to_pointer(self) -> AvatarPointer:
        """Convert the item to an avatar pointer."""
        return AvatarPointer(self.id, self.mime_type, file=BytesIO(self.image))


class PresenceEntry(NamedTuple):
    snowflake: int
    status: str
    changed_at: datetime


class StoreQueue(Generic[T]):
    """A queue for storing items to be sent to the store."""

    def __init__(self) -> None:
        self.__queue: Queue[T] = Queue()

    @property
    def queue(self) -> Queue[T]:
        return self.__queue

    async def push(self, item: T) -> None:
        """Push an item into the queue.

        If the queue is full, wait until a free slot
        is available before adding item.
        """
        await self.queue.put(item)

    async def pop(self) -> T:
        """Remove and return an item from the queue.

        If queue is empty, wait until an item is available.
        """
        return await self.queue.get()

    async def empty(self) -> bool:
        return self.queue.empty()

    async def size(self) -> int:
        return self.queue.qsize()

    def put_nowait(self, item: T) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available.

        Raises:
        -------
        `QueueFull`
            If the queue is full.
        """
        self.queue.put_nowait(item)

    def get_nowait(self) -> T:
        """Remove and return an item from the queue.

        Return an item if one is immediately available.

        Raises:
        -------
        `QueueEmpty`
            If the queue is empty.
        """
        return self.queue.get_nowait()

    def pop_fixed(self, n: int) -> list[T]:
        """Remove and return n items from the queue.

        Return a list of items if n items are immediately available.
        """
        items: list[T] = []

        for _ in range(n):
            try:
                items.append(self.get_nowait())
            except Exception:
                break

        if not items:
            raise QueueEmpty

        return items

    def __len__(self) -> int:
        return self.queue.qsize()


def type_of(data: bytes) -> str:
    mime = from_buffer(data, mime=True)
    if mime in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        return mime

    raise ValueError(f"Invalid mime type: {mime}")

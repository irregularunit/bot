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

from asyncio import Queue
from io import BytesIO
from typing import Generic, NamedTuple, TypeVar

from magic import from_buffer

from src.imaging import AvatarPointer

__all__: tuple[str, ...] = (
    "StoreQueueItems",
    "StoreQueue",
    "type_of",
)


ItemType = TypeVar("ItemType")
VALID_MIME_TYPES = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
)


class StoreQueueItems(NamedTuple):
    """A named tuple for items in the send queue."""

    id: int
    image: bytes
    mime_type: str

    def to_pointer(self) -> AvatarPointer:
        """Convert the item to an avatar pointer."""
        return AvatarPointer(self.id, self.mime_type, file=BytesIO(self.image))


class StoreQueue(Generic[ItemType]):
    """A queue for storing items to be sent to the store."""

    def __init__(self) -> None:
        self.__queue: Queue[ItemType] = Queue()

    @property
    def queue(self) -> Queue[ItemType]:
        return self.__queue

    async def push(self, item: ItemType) -> None:
        """Push an item into the queue.

        If the queue is full, wait until a free slot
        is available before adding item.
        """
        await self.queue.put(item)

    async def pop(self) -> ItemType:
        """Remove and return an item from the queue.

        If queue is empty, wait until an item is available.
        """
        return await self.queue.get()

    async def empty(self) -> bool:
        return self.queue.empty()

    async def size(self) -> int:
        return self.queue.qsize()

    def put_nowait(self, item: ItemType) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available.

        Raises:
        -------
        `QueueFull`
            If the queue is full.
        """
        self.queue.put_nowait(item)

    def get_nowait(self) -> ItemType:
        """Remove and return an item from the queue.

        Return an item if one is immediately available.

        Raises:
        -------
        `QueueEmpty`
            If the queue is empty.
        """
        return self.queue.get_nowait()

    def __len__(self) -> int:
        return self.queue.qsize()


def type_of(data: bytes) -> str:
    mime = from_buffer(data, mime=True)
    if mime in VALID_MIME_TYPES:
        return mime

    raise ValueError(f"Invalid mime type: {mime}")

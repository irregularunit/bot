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

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Self, Type

from discord.ext import tasks

if TYPE_CHECKING:
    from src.models.discord import SerenityUser

__all__: tuple[str, ...] = ("SerenityUserCache",)


@dataclass(slots=True)
class CachedEntity:
    entity: SerenityUser
    timestamp: float


class SerenityUserCache:
    def __init__(self, *users: SerenityUser, size: int = 100) -> None:
        self.__cache: dict[int, CachedEntity] = {
            user.id: CachedEntity(entity=user, timestamp=time.time()) for user in users
        }
        self.__size = size
        self.__invalidate.start()

    def get(self, snowflake: int, /) -> Optional[SerenityUser]:
        cached = self.__cache.get(snowflake)

        if cached is None:
            return None

        cached.timestamp = time.time()
        return cached.entity

    def push(self, snowflake: int, entity: SerenityUser, /) -> None:
        if len(self.__cache) >= self.__size:
            self.__evict()

        self.__cache[snowflake] = CachedEntity(
            entity=entity, timestamp=time.time())

    def insert_many(self, *entities: SerenityUser) -> None:
        for entity in entities:
            self.push(entity.id, entity)

    def pop(self, snowflake: int, /) -> Optional[SerenityUser]:
        cached = self.__cache.pop(snowflake, None)

        if cached is None:
            return None

        return cached.entity

    def __len__(self) -> int:
        return len(self.__cache)

    def __repr__(self) -> str:
        return f"<SerenityUserCache size={self.__size} length={len(self.__cache)} at {hex(id(self))}"

    def __evict(self) -> None:
        _, cached = min(self.__cache.items(),
                        key=lambda item: item[1].timestamp)
        del self.__cache[cached.entity.id]

        # TODO: combine with pop

    @tasks.loop(minutes=5)
    async def __invalidate(self) -> None:
        if len(self.__cache) < self.__size - (self.__size // 10):
            # No need to evict if we're not at capacity yet
            # We'll evict when we're at 90% capacity
            return

        while self.__cache:
            _, cached = min(self.__cache.items(),
                            key=lambda item: item[1].timestamp)

            # Remove all cached entities that are older than 30 minutes
            if time.time() - cached.timestamp < 1_800:
                break

            del self.__cache[cached.entity.id]

    @classmethod
    def from_none(cls: Type[Self], size: int = 100) -> Self:
        """Create a new cache from no users."""
        return cls(size=size)

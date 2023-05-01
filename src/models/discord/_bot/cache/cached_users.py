# -*- coding: utf-8 -*-

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Self, Type

from discord.ext import tasks

if TYPE_CHECKING:
    from src.models.discord import SerenityUser


__all__: tuple[str, ...] = ("SerenityUserCache",)


@dataclass
class CachedEntity:
    entity: SerenityUser
    timestamp: float


class SerenityUserCache:
    def __init__(self, *users: SerenityUser, size: int = 100) -> None:
        self.__cache: dict[int, CachedEntity] = {
            user.id: CachedEntity(entity=user, timestamp=time.time()) for user in users
        }
        self.__size = size
        self.__maintain.start()

    def get(self, snowflake: int, /) -> Optional[SerenityUser]:
        cached = self.__cache.get(snowflake)

        if cached is None:
            return None

        cached.timestamp = time.time()
        return cached.entity

    def push(self, snowflake: int, entity: SerenityUser, /) -> None:
        if len(self.__cache) >= self.__size:
            self.__evict()

        self.__cache[snowflake] = CachedEntity(entity=entity, timestamp=time.time())

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
        while self.__cache:
            _, cached = min(self.__cache.items(), key=lambda item: item[1].timestamp)

            if cached.entity is not None:
                del self.__cache[cached.entity.id]
                break

    @tasks.loop(minutes=5)
    async def __maintain(self) -> None:
        if len(self.__cache) < self.__size - (self.__size // 10):
            # No need to evict if we're not at capacity yet
            # We'll evict when we're at 90% capacity
            return

        while self.__cache:
            _, cached = min(self.__cache.items(), key=lambda item: item[1].timestamp)

            # Remove all cached entities that are older than 30 minutes
            if time.time() - cached.timestamp < 1_800:
                break

            if cached.entity is not None:
                del self.__cache[cached.entity.id]

    @classmethod
    def from_none(cls: Type[Self], size: int = 100) -> Self:
        """Create a new cache from no users."""
        return cls(size=size)

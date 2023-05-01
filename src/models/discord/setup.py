# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING

from ._guild import SerenityGuildManager
from ._user import SerenityUserManager

if TYPE_CHECKING:
    from asyncpg import Pool, Record

__all__: tuple[str, ...] = ("SerenityModelManager",)


class SerenityModelManager(SerenityUserManager, SerenityGuildManager):
    def __init__(self, pool: Pool[Record]) -> None:
        self.pool = pool
        super().__init__(pool)

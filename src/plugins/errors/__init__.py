# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING

from .plugin import Errors

if TYPE_CHECKING:
    from src.models.serenity import Serenity


async def setup(bot: Serenity) -> None:
    await bot.add_cog(Errors(bot))

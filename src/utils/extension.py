"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Optional

from discord.ext import commands

if TYPE_CHECKING:
    from bot import Bot

__all__: tuple[str, ...] = ("BaseExtension",)


class BaseExtension(commands.Cog):
    hidden: Optional[bool] = False

    def __init__(self, bot: Bot, *args: Any, **kwargs: Any) -> None:
        self.bot: Bot = bot
        self.id: int = int(str(int(uuid.uuid4()))[:20])

        pop_mro = next(iter(self.__class__.__mro__))
        if issubclass(pop_mro, self.__class__) or hasattr(pop_mro, "__jsk_instance__"):
            kwargs["bot"] = bot

        super().__init__(*args, **kwargs)

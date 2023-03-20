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

        next_in_mro = next(iter(self.__class__.__mro__))
        if hasattr(next_in_mro, "__jsk_instance__") or isinstance(next_in_mro, self.__class__):
            kwargs["bot"] = bot

        super().__init__(*args, **kwargs)

# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

from src.shared import Plugin
from src.interfaces import GuildMessagable
from .handlers import get_message

if TYPE_CHECKING:
    from src.models.discord import SerenityContext
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Errors",)


class Errors(Plugin):
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity

    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        self.logger.exception("Unhandled exception in event %s", event)

    @Plugin.listener("on_command_error")
    async def command_error_listener(
        self, ctx: SerenityContext, error: Exception
    ) -> None:
        if isinstance(ctx.channel, GuildMessagable):
            return
        
        hint = get_message(ctx, error)
        send = ctx.channel.permissions_for(ctx.me).send_messages

        if send and hint is not None:
            try:
                await ctx.safe_send(hint)
            except discord.HTTPException:
                pass

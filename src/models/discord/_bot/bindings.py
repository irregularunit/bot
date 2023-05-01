# -*- coding: utf-8 -*-

from discord import Intents

__all__: tuple[str, ...] = ("INTENTS",)


INTENTS = Intents(
    guilds=True,
    members=True,
    messages=True,
    message_content=True,
    presences=True,
)

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import sys
from logging import Logger, getLogger
from typing import Any

import discord

__all__: tuple[str, ...] = ("Gateway",)


log: Logger = getLogger(__name__)


class Gateway(discord.gateway.DiscordWebSocket):  # type: ignore
    async def identify(self) -> None:
        payload: dict[str, Any] = {
            "op": self.IDENTIFY,
            "d": {
                "token": self.token,
                "properties": {
                    "$os": sys.platform,
                    "$browser": "Discord Android",
                    "$device": "Discord Android",
                    "$referrer": "",
                    "$referring_domain": "",
                },
                "compress": True,
                "large_threshold": 250,
                "v": 10,
            },
        }

        if self.shard_id is not None and self.shard_count is not None:
            payload["d"]["shard"] = [self.shard_id, self.shard_count]

        state: Any = self._connection
        if state._activity is not None or state._status is not None:
            payload["d"]["presence"] = {
                "status": state._status,
                "game": state._activity,
                "since": 0,
                "afk": False,
            }

        if state._intents is not None:
            payload["d"]["intents"] = state._intents.value

        await self.call_hooks("before_identify", self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)
        log.info("Shard ID %s has sent the IDENTIFY payload.", self.shard_id)

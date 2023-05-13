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

from datetime import datetime, timedelta
from logging import Logger, getLogger
from typing import Any, Optional, Union

import discord

from src.shared import SerenityQueue

from .utils import AssetEntity, PresenceEntitiy, type_of

__all__: tuple[str, ...] = ("EventExtensionMixin",)


class EventExtensionMixin:
    """Mixin for the Serenity class that adds event-related functionality."""

    asset_queue: SerenityQueue[AssetEntity]
    asset_channel: Optional[discord.TextChannel]
    presence_queue: SerenityQueue[PresenceEntitiy]
    _presence_queue_active: bool
    _logger: Logger

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.asset_queue = SerenityQueue()
        self.asset_channel = None
        self.presence_queue = SerenityQueue()
        self._presence_queue_active = False
        self._logger = getLogger(__name__)

    @property
    def presence_queue_active(self) -> bool:
        return self._presence_queue_active

    @presence_queue_active.setter
    def presence_queue_active(self, value: bool) -> None:
        self._presence_queue_active = value

    def get_logger(self, event_name: str) -> Logger:
        return self._logger.getChild(event_name)

    async def read_avatar_asset(self, target: Union[discord.User, discord.Member]) -> Optional[bytes]:
        """Read the avatar asset for the given target."""
        logger = self.get_logger("read_avatar_asset")

        try:
            asset = target.avatar if isinstance(target, discord.User) else target.display_avatar

            if asset is None:
                # ``.read()`` should return the default
                # avatar but our linter doesn't know that
                asset = target.default_avatar

            avatar = await asset.read()
        except discord.HTTPException as exc:
            if exc.status in (403, 404):
                # 403: Forbidden
                # 404: Not Found
                # Discord has forsakes us, so we return
                return None
            if exc.status >= 500:
                # 5xx: Server Error
                # Discord is having issues, Let's try later
                await discord.utils.sleep_until(datetime.utcnow() + timedelta(minutes=1))
                return await self.read_avatar_asset(target)

            logger.exception(
                "An error occurred while reading the avatar asset for %s (%d)",
                target,
                target.id,
                exc_info=exc,
            )

            return None

        return avatar

    async def push_asset(self, snowflake: int, *, asset: bytes) -> None:
        try:
            mime = type_of(asset)
        except ValueError:
            # Not an valid image type and the type could not be determined
            return

        await self.asset_queue.put(AssetEntity(snowflake, asset, mime))

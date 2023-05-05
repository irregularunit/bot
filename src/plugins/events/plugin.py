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
from typing import TYPE_CHECKING, Optional, Union

import discord
from discord.ext import tasks
from typing_extensions import override

from src.shared import Plugin

from .utils import StoreQueue, StoreQueueItems, type_of

if TYPE_CHECKING:
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Events",)


class Events(Plugin):
    """A plugin for discord events."""

    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity
        self.queue: StoreQueue[StoreQueueItems] = StoreQueue()

    @override
    async def cog_load(self) -> None:
        self.empty_queue.start()

    @override
    async def cog_unload(self) -> None:
        # Gracefully stops the task and waits
        # for it to finish before ejecting it
        self.empty_queue.stop()

    async def _read_avatar_asset(
        self, target: Union[discord.Member, discord.User]
    ) -> Optional[bytes]:
        logger = self.logger.getChild("_read_avatar_asset")

        try:
            asset = (
                target.avatar
                if isinstance(target, discord.User)
                else target.display_avatar
            )

            if asset is None:
                # ``.read()`` should return the default
                # avatar but our linter doesn't know that
                asset = target.default_avatar

            avatar = await asset.read()
        except discord.HTTPException as exc:
            if exc.status in (403, 404):
                # 403: Forbidden
                # 404: Not Found
                # Discord has forsaken us, silently return
                return None
            if exc.status >= 500:
                # 5xx: Server Error
                # Discord is having issues, Let's try later
                await discord.utils.sleep_until(
                    datetime.utcnow() + timedelta(minutes=10)
                )
                return await self._read_avatar_asset(target)

            logger.exception(
                "Unexpected HTTPException (%s) while reading avatar for %s",
                exc.status,
                target.id,
            )

            return None

        return avatar

    async def _dump_members(self, *members: discord.Member) -> None:
        member_dump = "INSERT INTO serenity_users (snowflake, created_at) VALUES ($1, $2) ON CONFLICT DO NOTHING"
        created_at = discord.utils.utcnow()

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    member_dump, ((m.id, created_at) for m in members)
                )

    @Plugin.listener("on_guild_join")
    async def new_guild_event(self, guild: discord.Guild) -> None:
        logger = self.logger.getChild("new_guild_event")
        logger.info(
            "Joined guild %s (%s) with %s members",
            guild.name,
            guild.id,
            guild.member_count,
        )

        if guild.id not in self.serenity.cached_guilds:
            entity = await self.serenity.model_manager.get_or_create_guild(guild.id)
            self.serenity.set_guild(entity)

        members = await guild.chunk() if guild.chunked else guild.members

        for member in members:
            if len(member.mutual_guilds) > 1 or member.id == guild.me.id:
                continue

            avatar = await self._read_avatar_asset(member)

            if avatar is None:
                continue

            try:
                mime_type = type_of(avatar)
            except ValueError:
                logger.exception("Cannot determine mime type for %s", member.id)
                continue

            await self.queue.push(
                StoreQueueItems(
                    id=member.id,
                    image=avatar,
                    mime_type=mime_type,
                )
            )

        await self._dump_members(*members)

    @tasks.loop(minutes=5)
    async def empty_queue(self) -> None:
        logger = self.logger.getChild("empty_queue")
        logger.debug("Emptying queue")

        while not self.queue.empty():
            item = await self.queue.pop()
            logger.debug("Popped item %s", item.id)

            await item.to_pointer().save()

    @Plugin.listener("on_member_join")
    async def new_member_event(self, member: discord.Member) -> None:
        logger = self.logger.getChild("new_member_event")
        if member.id == member.guild.me.id or len(member.mutual_guilds) > 1:
            return

        avatar = await self._read_avatar_asset(member)

        if avatar is None:
            return

        try:
            mime_type = type_of(avatar)
        except ValueError:
            logger.exception("Cannot determine mime type for %s", member.id)
            return

        await self.queue.push(
            StoreQueueItems(
                id=member.id,
                image=avatar,
                mime_type=mime_type,
            )
        )

        await self._dump_members(member)

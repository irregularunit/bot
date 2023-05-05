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

from asyncio import QueueEmpty
from datetime import datetime, timedelta
from io import BytesIO
from logging import Logger
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
        self.queue_channel: Optional[discord.TextChannel] = None
        self.logger = self.serenity.logger.getChild("events")

    def _get_logger(self, event_name: str) -> Logger:
        return self.logger.getChild(event_name)

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
        logger = self._get_logger("_read_avatar_asset")

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

    async def _store_avatar(self, user_id: int, avatar: bytes) -> None:
        try:
            mime_type = type_of(avatar)
        except ValueError:
            self._get_logger("_store_avatar").exception(
                "Cannot determine mime type for %s", user_id
            )
            return

        await self.queue.push(
            StoreQueueItems(
                id=user_id,
                image=avatar,
                mime_type=mime_type,
            )
        )

    async def _dump_members(self, *members: discord.Member) -> None:
        insert_statement = """
            INSERT INTO
                serenity_users (snowflake, created_at)
            VALUES
                ($1, $2)
            ON CONFLICT DO NOTHING
        """
        created_at = discord.utils.utcnow()

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    insert_statement, ((m.id, created_at) for m in members)
                )

    @Plugin.listener("on_guild_join")
    async def new_guild_event(self, guild: discord.Guild) -> None:
        logger = self._get_logger("new_guild_event")
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
            # If you aren't on the latest 2.3.0a release or
            # commit:  252ac38 (1 parent 34a434b)
            # Then you have to try and except this
            # AttributeError: 'ClientUser' object has no attribute 'mutual_guilds'
            if len(member.mutual_guilds) > 1 or member.id == guild.me.id:
                continue

            avatar = await self._read_avatar_asset(member)

            if avatar is not None:
                await self._store_avatar(member.id, avatar)

        await self._dump_members(*members)

    @tasks.loop(minutes=1)
    async def empty_queue(self) -> None:
        logger = self._get_logger("empty_queue")
        logger.debug("Emptying queue")

        while not await self.queue.empty():
            try:
                item = self.queue.get_nowait()
            except QueueEmpty:
                break

            logger.debug("Popped item %s", item.id)

            await item.to_pointer().save()
            await self._send_to_ts(item)

    async def _send_to_ts(self, item: StoreQueueItems) -> None:
        logger = self._get_logger("_send_to_ts")

        if (channel := self.queue_channel) is None:
            channel = self.serenity.get_channel(self.serenity.config.TS_CHANNEL_ID)

            if not isinstance(channel, discord.TextChannel):
                logger.error(
                    "Invalid channel type %s for channel %s",
                    type(channel),
                    self.serenity.config.TS_CHANNEL_ID,
                )
                return

            self.queue_channel = channel

        try:
            file = discord.File(
                BytesIO(item.image),
                filename=f"{item.id}.{item.mime_type.split('/')[1]}",
            )
            message = await channel.send(f"New avatar for {item.id}", file=file)
        except (
            ValueError,
            discord.HTTPException,
        ) as exc:
            logger.exception(
                "Unexpected exception while sending avatar for %s",
                item.id,
                exc_info=exc,
            )
            return

        # We don't care about the user object here, but we need to
        # ensure the relationship is created in the database
        _ = await self.serenity.get_or_create_user(item.id)

        insert_statement = """
            INSERT INTO
                serenity_user_history (snowflake, item_name, item_value)
            VALUES
                ($1, $2, $3)
        """

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    insert_statement,
                    item.id,
                    "avatar",
                    message.attachments[0].url,
                )

    @Plugin.listener("on_member_join")
    async def new_member_event(self, member: discord.Member) -> None:
        if member.id == member.guild.me.id or len(member.mutual_guilds) > 1:
            return

        avatar = await self._read_avatar_asset(member)

        if avatar is not None:
            await self._store_avatar(member.id, avatar)

        await self._dump_members(member)

    async def _dump_user_history(
        self, user: discord.User, before: discord.User
    ) -> None:
        insert_statement = """
            INSERT INTO
                serenity_user_history (snowflake, item_name, item_value)
            VALUES
                ($1, $2, $3)
        """

        # Same as above, we don't care about the user object
        _ = await self.serenity.get_or_create_user(user.id)

        async with self.serenity.pool.acquire() as conn:
            async with conn.transaction():
                if before.name != user.name:
                    await conn.execute(
                        insert_statement,
                        user.id,
                        "name",
                        user.name,
                    )
                if before.discriminator != user.discriminator:
                    await conn.execute(
                        insert_statement,
                        user.id,
                        "discriminator",
                        user.discriminator,
                    )

    @Plugin.listener("on_member_update")
    async def member_update_event(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if (
            before.id == before.guild.me.id
            or len(before.mutual_guilds) > 1
            or (before.avatar == after.avatar)
        ):
            return

        avatar = await self._read_avatar_asset(after)

        if avatar is not None:
            await self._store_avatar(after.id, avatar)

    @Plugin.listener("on_user_update")
    async def user_update_event(
        self, before: discord.User, after: discord.User
    ) -> None:
        logger = self._get_logger("user_update_event")

        if not isinstance(self.serenity.user, discord.ClientUser):
            # Typecheckers are dumb v_v
            return logger.warning("Serenity hasn't initialized yet")

        if before.id == self.serenity.user.id:
            return

        await self._dump_user_history(after, before)

        if before.avatar != after.avatar:
            avatar = await self._read_avatar_asset(after)

            if avatar is not None:
                await self._store_avatar(after.id, avatar)

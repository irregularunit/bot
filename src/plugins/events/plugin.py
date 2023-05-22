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

from asyncio import QueueEmpty, sleep
from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks
from typing_extensions import override

from src.shared import Plugin

from ._base import EventExtensionMixin
from .utils import PRESENCE_STATUS, AssetEntity, PresenceEntitiy

if TYPE_CHECKING:
    from src.models.serenity import Serenity


__all__: tuple[str, ...] = ("Events",)


class Events(EventExtensionMixin, Plugin):
    @override
    def __init__(self, serenity: Serenity) -> None:
        self.serenity = serenity

        super().__init__()

    @override
    async def cog_load(self) -> None:
        self.empty_asset_queue.start()

    @override
    async def cog_unload(self) -> None:
        self.empty_asset_queue.stop()

    async def send_to_transcript(self, asset: AssetEntity) -> None:
        logger = self.get_logger("send_to_transcript")

        if self.asset_channel is None:
            channel = await self.serenity.fetch_channel(self.serenity.config.TS_CHANNEL_ID)

            if not isinstance(channel, discord.TextChannel):
                raise TypeError("Expected a text channel got %s", type(channel))

            self.asset_channel = channel

        try:
            file = discord.File(
                BytesIO(asset.image_data),
                filename=f"{asset.snowflake}.{asset.mime_type.split('/')[1]}",
            )
            message = await self.asset_channel.send(f"Now archiving {asset.snowflake}", file=file)
        except (ValueError, discord.HTTPException) as exc:
            logger.exception("Failed to archive asset %s", asset.snowflake)

            if isinstance(exc, discord.HTTPException):
                raise exc from None

            return

        await self.serenity.get_or_create_user(asset.snowflake)

        insert_statement = """
            INSERT INTO
                serenity_user_history (snowflake, item_name, item_value)
            VALUES
                ($1, $2, $3)
        """

        first_attachment = message.attachments[0]

        async with self.serenity.pool.acquire() as connection:
            await connection.execute(
                insert_statement,
                asset.snowflake,
                "avatar",
                first_attachment.url,
            )

    @tasks.loop(minutes=1)
    async def empty_asset_queue(self) -> None:
        logger = self.get_logger("empty_asset_queue")
        logger.debug("Emptying asset queue")

        while not self.asset_queue.empty():
            try:
                asset = self.asset_queue.get_nowait()
            except QueueEmpty:
                break

            logger.debug("Pushing asset %s to IO", asset.snowflake)
            await asset.to_pointer().save()

            await sleep(1.5)
            await self.send_to_transcript(asset)

    @tasks.loop(minutes=5)
    async def empty_presence_queue(self) -> None:
        logger = self.get_logger("empty_presence_queue")

        if self.presence_queue_active:
            logger.debug("Presence queue is active, skipping")
            return

        self.presence_queue_active = True

        while not self.presence_queue.empty():
            try:
                presences = await self.presence_queue.get_many(40)
            except QueueEmpty:
                break

            logger.info("Pushing %s presences to our database", len(presences))

            insert_statement = """
                INSERT INTO
                    serenity_user_presence (snowflake, status, changed_at)
                VALUES
                    ($1, $2, $3)
            """

            async with self.serenity.pool.acquire() as connection:
                await connection.executemany(
                    insert_statement,
                    ((p.snowflake, p.status, p.changed_at) for p in presences),
                )

        self.presence_queue_active = False

    async def dump_members(self, *members: discord.Member) -> None:
        insert_statement = """
            INSERT INTO
                serenity_users (snowflake, created_at)
            VALUES
                ($1, $2)
            ON CONFLICT DO NOTHING
        """
        created_at = discord.utils.utcnow()

        async with self.serenity.pool.acquire() as connection:
            await connection.executemany(
                insert_statement,
                ((member.id, created_at) for member in members),
            )

    async def dump_user_history(
        self,
        before: discord.User,
        after: discord.User,
    ) -> None:
        insert_statement = """
            INSERT INTO
                serenity_user_history (snowflake, item_name, item_value)
            VALUES
                ($1, $2, $3)
        """
        await self.serenity.get_or_create_user(after.id)

        async with self.serenity.pool.acquire() as connection:
            if before.name != after.name:
                await connection.execute(
                    insert_statement,
                    after.id,
                    "name",
                    after.name,
                )

            if before.discriminator != after.discriminator:
                await connection.execute(
                    insert_statement,
                    after.id,
                    "discriminator",
                    after.discriminator,
                )

    @Plugin.listener("on_guild_join")
    async def new_guild_event(self, guild: discord.Guild) -> None:
        logger = self.get_logger("new_guild_event")
        logger.info("Joined new guild %s with %s members", guild.name, guild.member_count)

        if guild.id not in self.serenity.cached_guilds:
            await self.serenity.get_or_create_guild(guild.id)

        members = await guild.chunk() if guild.chunked else guild.members

        for member in members:
            if len(member.mutual_guilds) > 1 or member.id == guild.me.id:
                continue

            asset = await self.read_avatar_asset(member)

            if asset is not None:
                await self.push_asset(member.id, asset=asset)

        await self.dump_members(*members)

    @Plugin.listener("on_member_join")
    async def new_member_event(self, member: discord.Member) -> None:
        if member.id == member.guild.me.id or len(member.mutual_guilds) > 1:
            return

        asset = await self.read_avatar_asset(member)

        if asset is not None:
            await self.push_asset(member.id, asset=asset)

        await self.dump_members(member)

    @Plugin.listener("on_member_update")
    async def member_update_event(self, before: discord.Member, after: discord.Member) -> None:
        if before.id == before.guild.me.id or len(before.mutual_guilds) > 1 or before.avatar == after.avatar:
            return

        asset = await self.read_avatar_asset(after)

        if asset is not None:
            await self.push_asset(after.id, asset=asset)

    @Plugin.listener("on_user_update")
    async def user_update_event(self, before: discord.User, after: discord.User) -> None:
        if before.avatar == after.avatar:
            return

        asset = await self.read_avatar_asset(after)

        if asset is not None:
            await self.push_asset(after.id, asset=asset)

        await self.dump_user_history(before, after)

    @Plugin.listener("on_presence_update")
    async def presence_update_event(self, before: discord.Member, after: discord.Member) -> None:
        if before.status == after.status:
            return

        if await self.serenity.redis.exists(f"{after.id}:RateLimit:PresenceUpdate"):
            return

        await self.serenity.redis.setex(
            name=f"{after.id}:RateLimit:PresenceUpdate",
            time=5,
            value="Ratelimit reached for presence update",
        )

        if self.serenity.user_cache.get(after.id) is None:
            await self.serenity.get_or_create_user(after.id)

        if not (status := PRESENCE_STATUS.get(after.status)):
            return

        await self.presence_queue.put(PresenceEntitiy(after.id, status, discord.utils.utcnow()))

    @Plugin.listener("on_message")
    async def message_event(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        if message.author == self.serenity.user or self.serenity.user is None:
            return

        ctx = await self.serenity.get_context(message)

        if message.content in [
            f"<@{self.serenity.user.id}>",
            f"<@!{self.serenity.user.id}>",
        ]:
            if ctx.bot_permissions.send_messages is False:
                return

            command = self.serenity.get_command("about")

            if command is None:
                return

            await ctx.invoke(command)  # type: ignore

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import asyncio
import re
import uuid as uuid_lib
from datetime import datetime, timezone
from io import BytesIO
from logging import Logger, getLogger
from typing import TYPE_CHECKING, NamedTuple, Optional, Sequence

import discord
from discord.ext import commands, tasks

from models import Guild
from utils import BaseExtension, owo_command_set, resize_to_limit, type_of

if TYPE_CHECKING:
    from bot import Bot

__all__: tuple[str, ...] = ("DiscordEventListener",)

log: Logger = getLogger(__name__)


class SendQueueItem(NamedTuple):
    user_id: int
    name: str | None
    image: bytes


class DiscordEventListener(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

        self._is_running: bool = False
        self._send_queue: list[SendQueueItem] = []
        self._push_items: str = "SELECT insert_avatar_history_item($1, $2, $3)"
        self._presence_map: dict[discord.Status, str] = {
            discord.Status.online: "Online",
            discord.Status.idle: "Idle",
            discord.Status.dnd: "Do Not Disturb",
        }
        self.cached_channel: Optional[discord.TextChannel] = None
        self.__owo_hunt_commands: tuple[str, ...] = ("hunt", "h", "catch")
        self.__owo_battle_commands: tuple[str, ...] = ("b", "battle", "fight")
        self.__owo_std_commands: tuple[str, ...] = ("owo", "uwu")
        self.send_queue_task.start()

    @staticmethod
    def message_timestamp_to_datetime_with_tz(timestamp: float) -> datetime:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def push_item(self, user_id: int, name: str | None, image: bytes, /) -> None:
        self._send_queue.append(SendQueueItem(user_id, name, image))

    async def _read_avatar(self, member: discord.Member) -> Optional[bytes]:
        try:
            avatar: bytes = await member.display_avatar.read()
        except discord.HTTPException as exc:
            if exc.status in (403, 404):
                # Discord has forsaken us. Most likely due to an invalid avatar
                return
            elif exc.status >= 500:
                # Discord is having issues. Let's try again later
                await asyncio.sleep(15.0)
                await self._read_avatar(member)
            return log.exception(
                "Unhandled Discord HTTPException while getting avatar for %s (%s)", member.name, member.id
            )

        return avatar

    @tasks.loop(seconds=30)
    async def send_queue_task(self) -> None:
        if not self._send_queue or self._is_running:
            return

        self.cached_channel = self.cached_channel or await self.bot.fetch_channel(1086710517323804924)  # type: ignore
        assert isinstance(self.cached_channel, discord.TextChannel)

        self._is_running = True
        item: SendQueueItem = self._send_queue.pop(0)
        try:
            message: discord.Message = await self.cached_channel.send(
                content=f"{item.name} ({item.user_id})",
                file=discord.File(BytesIO(item.image), filename=f"{uuid_lib.uuid4()}.{type_of(item.image)}"),
            )
        except Exception as exc:
            log.exception("Failed to send message to channel", exc_info=exc)
            self._send_queue.insert(0, item)
            self._is_running = False
            return

        query: str = "INSERT INTO item_history (uuid, item_type, item_value) VALUES ($1, $2, $3)"

        async with self.bot.pool.acquire() as connection:
            await connection.execute(query, item.user_id, "avatar", message.attachments[0].url)

        self._is_running = False
        log.info("Succesfully sent item %s to channel", message.content)

    @send_queue_task.before_loop
    async def before_send_queue_task(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener("on_guild_join")
    async def handle_guild_join(self, guild: discord.Guild) -> None:
        _log: Logger = log.getChild("manage_new_guild")

        _log.info("New guild joined: %s (%s)", guild.name, guild.id)
        self.bot.cached_guilds[guild.id] = await self.bot.manager.get_or_create_guild(guild.id)

        members: Sequence[discord.Member] | list[discord.Member] = (
            await guild.chunk() if guild.chunked else guild.members
        )
        to_queue: list[SendQueueItem] = []
        for member in members:
            try:
                if len(member.mutual_guilds) > 1:
                    continue
            except AttributeError:
                _log.debug("Skipping member %s (%s) due to AttributeError", member.name, member.id)
                continue
            try:
                avatar: bytes = await member.display_avatar.read()
            except discord.HTTPException as exc:
                if exc.status in (403, 404):
                    # Discord has forsaken us, most likely due to a invalid avatar
                    continue
                elif exc.status >= 500:
                    # We pass on this error, it's cause by discord
                    continue
                log.info("Unhandled Discord HTTPException while getting avatar for %s (%s)", member.name, member.id)
                continue

            avatar = resize_to_limit(BytesIO(avatar)).getvalue()
            inst: SendQueueItem = SendQueueItem(member.id, member.name, avatar)

            self._send_queue.append(inst)
            to_queue.append(inst)

        member_query: str = "INSERT INTO users (uuid, created_at) VALUES ($1, $2) ON CONFLICT DO NOTHING;"
        created_at: datetime = discord.utils.utcnow()

        async with self.bot.pool.acquire() as connection:
            await connection.executemany(member_query, [(member.id, created_at) for member in members])
            await connection.executemany(self._push_items, to_queue)

    @commands.Cog.listener("on_member_join")
    async def manage_new_member(self, member: discord.Member) -> None:
        if member.bot:
            return

        if len(member.mutual_guilds) > 1:
            return

        avatar: bytes | None = await self._read_avatar(member)
        if avatar is None:
            return

        avatar = resize_to_limit(BytesIO(avatar)).getvalue()
        self.push_item(member.id, member.name, avatar)

        query: str = "INSERT INTO users (uid, created_at) VALUES ($1, $2) ON CONFLICT DO NOTHING;"

        async with self.bot.pool.acquire() as connection:
            await connection.execute(query, member.id, discord.utils.utcnow())

    @commands.Cog.listener("on_member_update")
    async def manage_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.bot:
            return

        if before.display_avatar != after.display_avatar:
            avatar: bytes | None = await self._read_avatar(after)
            if avatar is None:
                return

            avatar = resize_to_limit(BytesIO(avatar)).getvalue()
            self.push_item(after.id, after.name, avatar)

    @commands.Cog.listener("on_user_update")
    async def manage_user_update(self, before: discord.User, after: discord.User) -> None:
        if before.name != after.name:
            query = "INSERT INTO item_history (uuid, item_type, item_value) VALUES ($1, $2, $3)"

            async with self.bot.pool.acquire() as connection:
                await connection.execute(query, after.id, "name", after.name)

        if before.discriminator != after.discriminator:
            query = "INSERT INTO item_history (uuid, item_type, item_value) VALUES ($1, $2, $3)"

            async with self.bot.pool.acquire() as connection:
                await connection.execute(query, after.id, "discriminator", after.discriminator)

    @commands.Cog.listener("on_guild_remove")
    async def manage_guild_leave(self, guild: discord.Guild) -> None:
        query: str = "DELETE FROM guilds WHERE uuid = $1"

        async with self.bot.pool.acquire() as connection:
            await connection.execute(query, guild.id)

    @commands.Cog.listener("on_presence_update")
    async def manage_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.bot:
            return

        if before.status != after.status:
            if await self.bot.redis.client.get(f"status:{after.id}"):
                # Discord dispatches this event for every guild the user is in.
                # Why? I don't know. But we don't want to insert the same data twice.
                return

            await self.bot.redis.client.setex(f"status:{after.id}", 3, 0)
            query: str = "INSERT INTO presence_history (uuid, status, status_before) VALUES ($1, $2, $3)"

            async with self.bot.pool.acquire() as connection:
                await connection.execute(
                    query,
                    after.id,
                    self._presence_map.get(after.status, "Offline"),
                    self._presence_map.get(before.status, "Offline"),
                )

    async def insert_counting(self, uid: int, message: discord.Message, word: str, time: int) -> None:
        if await self.bot.redis.client.get(f"{word}:{uid}"):
            # The user is most likely spamming to increase their score.
            return

        assert message.guild is not None
        await self.bot.redis.client.setex(f"{word}:{uid}", 60, time)

        _log: Logger = log.getChild("insert_counting")
        _log.debug("Inserting %s for %s at %s", word, uid, message.created_at.timestamp())

        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO owo_counting (uuid, gid, word, created_at) VALUES ($1, $2, $3, $4)",
                uid,
                message.guild.id,
                word,
                self.message_timestamp_to_datetime_with_tz(message.created_at.timestamp()),
            )

    @commands.Cog.listener("on_message")
    async def manage_messages(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return

        if not message.guild.id in self.bot.cached_guilds:
            self.bot.cached_guilds[message.guild.id] = await self.bot.manager.get_or_create_guild(message.guild.id)

        current_guild: Guild = self.bot.cached_guilds[message.guild.id]
        if not current_guild.owo_counting:
            return

        content: str = message.content.lower()
        maybe_safe: str = ""

        # I know we "should" use casefold, but it's not needed in
        # this case, since we're only using a subset of ASCII characters.
        if content.startswith(current_guild.owo_prefix):
            maybe_safe: str = content[len(current_guild.owo_prefix) :].strip().split(" ")[0].lower()

            if not maybe_safe:
                if not any(content.startswith(prefix) for prefix in self.__owo_std_commands):
                    # Prefix only message, we don't care.
                    return

        elif any(content.startswith(prefix) for prefix in self.__owo_std_commands):
            maybe_safe: str = content[3:].strip().split(" ")[0].lower()

        # We handle hunt and battle first, so we can drop all the others later without
        # having to check for them in the validation function. Which makes it faster.
        if maybe_safe in self.__owo_hunt_commands:
            await self.insert_counting(message.author.id, message, "hunt", 15)

        elif maybe_safe in self.__owo_battle_commands:
            await self.insert_counting(message.author.id, message, "battle", 15)

        elif maybe_safe in owo_command_set:
            # Returns True if the command exists in the hash map, False otherwise.
            await self.insert_counting(message.author.id, message, "owo", 10)

    @commands.Cog.listener("on_message")
    async def manage_prefix_change(self, message: discord.Message) -> None:
        if message.author.id != self.bot.config.owo_bot_id:
            return

        if not message.guild or not message.content:
            return

        successfuly_responses: tuple[str, str] = (
            "you successfully changed my server prefix to",
            "the current prefix is set to",
        )

        if not any(response in message.content for response in successfuly_responses):
            return

        if not (match := re.search(r"`(.*?)`", message.content)):
            return

        prefix = match.group(1)

        if not (guild := self.bot.cached_guilds.get(message.guild.id)):
            guild = await self.bot.manager.get_or_create_guild(message.guild.id)

        new_guild: Guild = await self.bot.manager.set_guild_owo_prefix(guild, prefix)
        self.bot.cached_guilds[message.guild.id] = new_guild

        try:
            await message.add_reaction(self.bot.config.owo_emote)
        except (
            discord.HTTPException,
            discord.Forbidden,
        ) as exc:
            _log: Logger = log.getChild("manage_prefix_change")
            _log.warning("Failed to add reaction to prefixed message: %s", exc)


async def setup(bot: Bot) -> None:
    await bot.add_cog(DiscordEventListener(bot))

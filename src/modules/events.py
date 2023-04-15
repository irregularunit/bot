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
from discord.ext.commands.converter import PartialMessageConverter

from models import EmbedBuilder, Guild
from utils import BaseExtension, owo_command_set, resize_to_limit, type_of

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("DiscordEventListener",)

log: Logger = getLogger(__name__)
AVATAR_CHANNEL_ID: int = 1094282348469702677


class SendQueueItem(NamedTuple):
    user_id: int
    name: str | None
    image: bytes


class PartialMessageView(discord.ui.View):
    def __init__(self, message: discord.Message, embed: EmbedBuilder) -> None:
        super().__init__(timeout=60.0)
        self.message: discord.Message = message
        self.embed: EmbedBuilder = embed

        self.add_item(
            discord.ui.Button(
                label="Jump to message",
                style=discord.ButtonStyle.link,
                url=message.jump_url,
            )
        )

    async def send_to_ctx(self, ctx: Context) -> None:
        await ctx.send(embed=self.embed, view=self)


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
    def timestamp_to_tztime(timestamp: float) -> datetime:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def push_item(self, user_id: int, name: str | None, image: bytes, /) -> None:
        self._send_queue.append(SendQueueItem(user_id, name, image))

    async def _read_avatar(self, member: discord.Member | discord.User) -> Optional[bytes]:
        try:
            avatar: bytes = await member.display_avatar.read()
        except discord.HTTPException as exc:
            if exc.status in (403, 404):
                # Discord has forsaken us. Most likely due to an invalid avatar
                return
            if exc.status >= 500:
                # Discord is having issues. Let's try again later
                await asyncio.sleep(15.0)
                await self._read_avatar(member)
            return log.exception(
                "Unhandled Discord HTTPException while getting avatar for %s (%s)",
                member.name,
                member.id,
            )

        return avatar

    @tasks.loop(seconds=30)
    async def send_queue_task(self) -> None:
        if not self._send_queue or self._is_running:
            return

        avatar_channel = self.cached_channel or await self.bot.fetch_channel(AVATAR_CHANNEL_ID)
        if not isinstance(avatar_channel, discord.TextChannel):
            raise RuntimeError("Avatar channel is not a text channel")

        self.cached_channel = avatar_channel

        self._is_running = True
        item: SendQueueItem = self._send_queue.pop(0)
        try:
            message: discord.Message = await self.cached_channel.send(
                content=f"`{item.name}` `({item.user_id})`",
                file=discord.File(
                    BytesIO(item.image),
                    filename=f"{uuid_lib.uuid4()}.{type_of(item.image)}",
                ),
            )
        except (
            discord.HTTPException,  # Forbidden inbound
            ValueError,  # file is too large (shouldn't happen)
        ) as exc:
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
                _log.debug(
                    "Skipping member %s (%s) due to AttributeError",
                    member.name,
                    member.id,
                )
                continue
            try:
                avatar: bytes = await member.display_avatar.read()
            except discord.HTTPException as exc:
                if exc.status in (403, 404):
                    # Discord has forsaken us, most likely due to a invalid avatar
                    continue
                if exc.status >= 500:
                    # We pass on this error, it's cause by discord
                    continue
                log.info(
                    "Unhandled Discord HTTPException while getting avatar for %s (%s)",
                    member.name,
                    member.id,
                )
                continue

            scaled_avatar: BytesIO = await self.bot.to_thread(resize_to_limit, BytesIO(avatar))
            inst: SendQueueItem = SendQueueItem(member.id, member.name, scaled_avatar.getvalue())

            self._send_queue.append(inst)
            to_queue.append(inst)

        member_query: str = (
            "INSERT INTO users (uuid, created_at) VALUES ($1, $2) ON CONFLICT DO NOTHING;"
        )
        created_at: datetime = discord.utils.utcnow()

        async with self.bot.pool.acquire() as connection:
            await connection.executemany(
                member_query, [(member.id, created_at) for member in members]
            )
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

        scaled_avatar: BytesIO = await self.bot.to_thread(resize_to_limit, BytesIO(avatar))
        self.push_item(member.id, member.name, scaled_avatar.getvalue())

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

            scaled_avatar: BytesIO = await self.bot.to_thread(resize_to_limit, BytesIO(avatar))
            self.push_item(after.id, after.name, scaled_avatar.getvalue())

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

        if before.avatar != after.avatar:
            avatar: bytes | None = await self._read_avatar(after)
            if avatar is None:
                return

            scaled_avatar: BytesIO = await self.bot.to_thread(resize_to_limit, BytesIO(avatar))
            self.push_item(after.id, after.name, scaled_avatar.getvalue())

            query: str = "SELECT insert_avatar_history_item($1, $2, $3)"
            async with self.bot.pool.acquire() as connection:
                await connection.execute(query, after.id, type_of(avatar), avatar)

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
            query: str = (
                "INSERT INTO presence_history (uuid, status, status_before) VALUES ($1, $2, $3)"
            )

            async with self.bot.pool.acquire() as connection:
                await connection.execute(
                    query,
                    after.id,
                    self._presence_map.get(after.status, "Offline"),
                    self._presence_map.get(before.status, "Offline"),
                )

    async def insert_counting(
        self, uid: int, message: discord.Message, word: str, time: int
    ) -> None:
        if await self.bot.redis.client.get(f"{word}:{uid}"):
            # The user is most likely spamming to increase their score.
            return

        if message.guild is None:
            raise AssertionError

        await self.bot.redis.client.setex(f"{word}:{uid}", 60, time)

        _log: Logger = log.getChild("insert_counting")
        _log.info(
            "Inserting %s for %s at %s",
            word,
            uid,
            message.created_at.timestamp(),
        )

        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO owo_counting (uuid, gid, word, created_at) VALUES ($1, $2, $3, $4)",
                uid,
                message.guild.id,
                word,
                self.timestamp_to_tztime(message.created_at.timestamp()),
            )

    @commands.Cog.listener("on_message")
    async def manage_messages(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return

        if not (
            current_guild := await self.bot.manager.get_or_create_guild(message.guild.id)
        ).owo_counting:
            return

        content: str = message.content.lower()
        maybe_safe: str = ""

        if content.startswith(current_guild.owo_prefix):
            maybe_safe: str = content[len(current_guild.owo_prefix) :].strip().split(" ")[0].lower()

            if not maybe_safe and not any(
                content.startswith(prefix) for prefix in self.__owo_std_commands
            ):
                # Custom prefix only message
                return

        elif any(content.startswith(prefix) for prefix in self.__owo_std_commands):
            maybe_safe: str = content[3:].strip().split(" ")[0].lower()
        else:
            return

        # We handle hunt and battle first, so we can drop all the others later without
        # having to check for them in the validation function. Which makes it faster.
        if maybe_safe in self.__owo_hunt_commands:
            await self.insert_counting(message.author.id, message, "hunt", 15)

        if maybe_safe in self.__owo_battle_commands:
            await self.insert_counting(message.author.id, message, "battle", 15)

        if maybe_safe not in owo_command_set:
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
            # HTTPException is an ancestor of Forbidden,
            # so we don't need to catch it separately.
        ) as exc:
            _log: Logger = log.getChild("manage_prefix_change")
            _log.warning("Failed to add reaction to prefixed message: %s", exc)

    @commands.Cog.listener("on_message")
    async def partial_message_handler(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        try:
            ctx = await self.bot.get_context(message)
            partial_message = await PartialMessageConverter().convert(ctx, message.content)
        except (commands.BadArgument, commands.CommandError):
            return
        else:
            qualified_message = await message.channel.fetch_message(partial_message.id)
            embed = EmbedBuilder.from_message(qualified_message)

            view = PartialMessageView(qualified_message, embed)
            await view.send_to_ctx(ctx)

            await message.delete()


async def setup(bot: Bot) -> None:
    await bot.add_cog(DiscordEventListener(bot))

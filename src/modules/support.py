"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory
from models import EmbedBuilder
from utils import BaseExtension, async_all, get_random_emoji

from .transparency import SafetyPrompt

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("SupportServer",)

log: logging.Logger = logging.getLogger(__name__)


SUPPORT_GUILD_ID: int = 1094278795239899156
WELCOME_CHANNEL_ID: int = 1094279453657546905
RULE_CHANNEL_ID: int = 1094284453276287007
PIT_INFORMATION_CHANNEL_ID: int = 1094282030726008872
PIT_QUEUE_CHANNEL_ID: int = 1094316098993803444


def is_support_server():
    def predicate(ctx: Context) -> bool:
        allowed = ctx.guild.id == SUPPORT_GUILD_ID

        if not allowed:
            raise UserFeedbackExceptionFactory.create(
                "This command can only be used in the support server.",
                ExceptionLevel.INFO,
            )

        return allowed

    return commands.check(predicate)


class SupportServer(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.cached_welcome_channel: Optional[discord.TextChannel] = None
        self.cached_pit_queue_channel: Optional[discord.TextChannel] = None

    async def cog_check(self, ctx: Context) -> bool:  # skipcq: PYL-R0201
        checks = [
            commands.guild_only(),
            is_support_server(),
        ]
        return await async_all(check(ctx) for check in checks)

    @staticmethod
    def plural(n: int) -> str:
        return (
            "th"
            if 4 <= n % 100 <= 20
            else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        )

    async def cache_channel(self, which: str) -> discord.TextChannel:
        if which == "welcome":
            wchannel = await self.bot.fetch_channel(WELCOME_CHANNEL_ID)

            if not isinstance(wchannel, discord.TextChannel):
                raise RuntimeError("Welcome channel is not a text channel")

            self.cached_welcome_channel = wchannel
            return self.cached_welcome_channel

        if which == "pit_queue":
            pchannel = await self.bot.fetch_channel(PIT_QUEUE_CHANNEL_ID)

            if not isinstance(pchannel, discord.TextChannel):
                raise RuntimeError("Pit queue channel is not a text channel")

            self.cached_pit_queue_channel = pchannel
            return self.cached_pit_queue_channel

        raise ValueError("Invalid channel type")

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != SUPPORT_GUILD_ID:
            return

        if self.cached_welcome_channel is None:
            self.cached_welcome_channel = await self.cache_channel("welcome")

        if not member.bot:
            join_position: int = len(self.cached_welcome_channel.guild.members)
            embed: EmbedBuilder = EmbedBuilder(
                title="We're glad to have you here!",
                description=(
                    f"""Welcome to the **Friendica Assembly**, {member.mention}!

                    Please read the rules and enjoy your stay!
                    > {get_random_emoji()} **Rules:** <#{RULE_CHANNEL_ID}>
                    > {get_random_emoji()} **Informaton:** <#{PIT_INFORMATION_CHANNEL_ID}>

                    You're our {join_position}{self.plural(join_position)} member!
                    """
                ),
            ).set_thumbnail(url=member.guild.icon)

            CLIENT_ROLE_ID: int = 1094280386537853019
            client_role: discord.Role | None = member.guild.get_role(
                CLIENT_ROLE_ID
            )

            if client_role is None:
                raise RuntimeError("Client role not found")
            
            if client_role not in member.roles:
                await member.add_roles(client_role)

            await self.cached_welcome_channel.send(embed=embed)
        else:
            DRONES_ROLE_ID: int = 1094280797604814868
            drones_role: discord.Role | None = member.guild.get_role(
                DRONES_ROLE_ID
            )

            if drones_role is None:
                raise RuntimeError("Drones role not found")

            if len(member.roles) > 1 and member.id not in (self.bot.user.id,):
                await member.kick(
                    reason="Bot has a custom role and was invited with permissions"
                )
                return

            if drones_role not in member.roles:
                await member.add_roles(drones_role)

            if self.cached_pit_queue_channel is None:
                self.cached_pit_queue_channel = await self.cache_channel(
                    "pit_queue"
                )

            async with self.bot.pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM bot_pits WHERE appid = $1 AND pending = TRUE",
                    member.id,
                )

            if result:
                await member.kick(reason="Bot was already approved")
            else:
                async with self.bot.pool.acquire() as conn:
                    res = await conn.fetchrow(
                        "SELECT * FROM bot_pits WHERE appid = $1 AND pending = FALSE",
                        member.id,
                    )

                    if not res:
                        await member.kick(
                            reason="Bot never applied for approval"
                        )
                        return

                embed = EmbedBuilder(
                    title="Bot Approved",
                    description=(
                        f"""**ℹ️ |** - {member.name} has been approved and granted access to the server.

                        > **Reason:** {res["reason"]}
                        > **Requestor:** <@{res["uuid"]}>
                        """
                    ),
                ).set_thumbnail(url=member.avatar)

                await self.cached_pit_queue_channel.send(embed=embed)

    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != SUPPORT_GUILD_ID:
            return

        if self.cached_welcome_channel is None:
            await self.cache_channel("welcome")

        if not member.bot:
            return

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM bot_pits WHERE appid = $1",
                member.id,
            )

        if self.cached_pit_queue_channel is None:
            self.cached_pit_queue_channel = await self.cache_channel(
                "pit_queue"
            )

        await self.cached_pit_queue_channel.send(
            f"**ℹ️ |** - {member.name} has been removed from the server.\n"
        )

    @commands.group(
        name="add",
        invoke_without_command=True,
    )
    async def add(self, ctx: Context) -> None:
        await ctx.send_help()

    @add.command(name="bot", aliases=("app",))
    async def add_bot(
        self,
        ctx: Context,
        bot: discord.User,
        *,
        reason: commands.clean_content,
    ) -> None:
        if not bot.bot:
            raise UserFeedbackExceptionFactory.create(
                "The specified user is not a bot.",
                ExceptionLevel.INFO,
            )

        if bot in ctx.guild.members:
            raise UserFeedbackExceptionFactory.create(
                "The specified bot is already in the server.",
                ExceptionLevel.INFO,
            )

        async with self.bot.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM bot_pits WHERE uuid = $1 AND appid = $2 AND pending = TRUE",
                ctx.author.id,
                bot.id,
            )

        if result is not None:
            raise UserFeedbackExceptionFactory.create(
                "You already have a bot pending approval.",
                ExceptionLevel.INFO,
            )

        prompt = SafetyPrompt(ctx.author)

        message: discord.Message | None = await ctx.safe_send(
            f"""
            {ctx.author.mention}, please read the following before continuing:
            > The bot must not use prefixes which are already in use by other bots.
            > No NSFW content is allowed and we encourage you to handle this in your code.
            """,
            view=prompt,
        )

        await prompt.wait()

        if prompt.confirmed:
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO bot_pits (uuid, appid, reason) VALUES ($1, $2, $3)",
                    ctx.author.id,
                    bot.id,
                    reason,
                )

            if self.cached_pit_queue_channel is None:
                self.cached_pit_queue_channel = await self.cache_channel(
                    "pit_queue"
                )

            invite: str = discord.utils.oauth_url(
                bot.id,
                guild=self.cached_pit_queue_channel.guild,
                scopes=("bot",),
                permissions=discord.Permissions(0),
            )

            embed: EmbedBuilder = EmbedBuilder(
                title="New bot pending approval",
                description=(
                    f"""
                    {ctx.author.name} has submitted a bot for approval.
                    > **Bot:** {bot.name}
                    > **Reason:** {reason}
                    > **Safe invite:** [invite]({invite})
                    """
                ),
            ).set_thumbnail(url=bot.display_avatar)

            await self.cached_pit_queue_channel.send(embed=embed)

        if message:
            await message.delete()

    @commands.has_guild_permissions(manage_guild=True)
    @commands.command(name="approve")
    async def approve(self, ctx: Context, bot: discord.User) -> None:
        if not bot.bot:
            raise UserFeedbackExceptionFactory.create(
                "The specified user is not a bot.",
                ExceptionLevel.INFO,
            )

        async with self.bot.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM bot_pits WHERE appid = $1 AND pending = TRUE",
                bot.id,
            )

        if result is None:
            raise UserFeedbackExceptionFactory.create(
                "The specified bot is not pending approval.",
                ExceptionLevel.INFO,
            )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "UPDATE bot_pits SET pending = FALSE WHERE appid = $1",
                bot.id,
            )

        if self.cached_pit_queue_channel is None:
            self.cached_pit_queue_channel = await self.cache_channel(
                "pit_queue"
            )

        await self.cached_pit_queue_channel.send(
            f"**ℹ️ |** - {bot.name} has been approved."
        )
        await ctx.message.add_reaction("✅")

    @commands.has_guild_permissions(manage_guild=True)
    @commands.command(name="deny")
    async def deny(self, ctx: Context, bot: discord.User) -> None:
        if not bot.bot:
            raise UserFeedbackExceptionFactory.create(
                "The specified user is not a bot.",
                ExceptionLevel.INFO,
            )

        async with self.bot.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM bot_pits WHERE appid = $1 AND pending = TRUE",
                bot.id,
            )

        if result is None:
            raise UserFeedbackExceptionFactory.create(
                "The specified bot is not pending approval.",
                ExceptionLevel.INFO,
            )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM bot_pits WHERE appid = $1",
                bot.id,
            )

        if self.cached_pit_queue_channel is None:
            self.cached_pit_queue_channel = await self.cache_channel(
                "pit_queue"
            )

        await self.cached_pit_queue_channel.send(
            f"**ℹ️ |** - {bot.name} has been denied."
        )
        await ctx.message.add_reaction("✅")


async def setup(bot: Bot) -> None:
    await bot.add_cog(SupportServer(bot))

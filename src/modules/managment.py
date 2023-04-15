"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory
from models import EmbedBuilder, User
from utils import BaseExtension, EmojiConverter, async_all, for_all_callbacks, get_random_emoji
from views import EmoteUnit, EmoteView

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("Managment",)

log: logging.Logger = logging.getLogger(__name__)


@for_all_callbacks(commands.cooldown(1, 3, commands.BucketType.user))
class Managment(BaseExtension):
    """Managment commands for the bot.
    
    Attributes
    ----------
    bot: `Bot`
        The bot instance.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    async def cog_check(self, ctx: Context) -> bool:  # skipcq: PYL-R0201
        """Check that the command is being run in a guild.
        
        Parameters
        ----------
        ctx: `Context`
            The context of the command.

        Returns
        -------
        `bool`
            Whether the command is being run in a guild.
        """
        checks = [commands.guild_only()]
        return await async_all(check(ctx) for check in checks)

    @staticmethod
    def compile_prefixes(prefixes: list[str]) -> re.Pattern[str]:

        return re.compile(
            r"|".join(re.escape(prefix) + r"\s*" for prefix in prefixes),
            re.IGNORECASE,
        )

    @commands.has_guild_permissions(administrator=True)
    @commands.group(name="prefix", invoke_without_command=True)
    async def prefix(self, ctx: Context, *, prefix: str) -> None:
        if (guild := self.bot.cached_guilds.get(ctx.guild.id)) is None:
            guild = await self.bot.manager.get_or_create_guild(ctx.guild.id)

        self.bot.cached_guilds[guild.id] = await self.bot.manager.add_guild_prefix(guild, prefix)
        self.bot.cached_prefixes[ctx.guild.id] = await self.bot.to_thread(
            self.compile_prefixes,
            self.bot.cached_guilds[ctx.guild.id].prefixes,
        )

        await ctx.safe_send(f"Added `{prefix}` to the guild's prefixes.")

    @prefix.command(name="remove", aliases=("rm",))
    async def prefix_remove(self, ctx: Context, *, prefix: str) -> None:
        if (guild := self.bot.cached_guilds.get(ctx.guild.id)) is None:
            guild = await self.bot.manager.get_or_create_guild(ctx.guild.id)

        self.bot.cached_guilds[guild.id] = await self.bot.manager.remove_guild_prefix(guild, prefix)
        self.bot.cached_prefixes[ctx.guild.id] = await self.bot.to_thread(
            self.compile_prefixes,
            self.bot.cached_guilds[ctx.guild.id].prefixes,
        )

        await ctx.safe_send(f"Removed `{prefix}` from the guild's prefixes.")

    @prefix.command(name="list", aliases=("ls",))
    async def prefix_list(self, ctx: Context) -> None:
        if (guild := self.bot.cached_guilds.get(ctx.guild.id)) is None:
            guild = await self.bot.manager.get_or_create_guild(ctx.guild.id)

        embed: EmbedBuilder = (
            EmbedBuilder()
            .set_author(name=f"{get_random_emoji()} Prefix settings for {ctx.guild.name}")
            .set_footer(
                text="Made with ❤️ by irregularunit.",
                icon_url=self.bot.user.display_avatar,
            )
            .add_field(
                name="Configured prefixes",
                value=(
                    ">>> " + "\n".join(f"`{prefix}`" for prefix in guild.prefixes)
                    if guild.prefixes
                    else "No prefixes configured."
                ),
                inline=False,
            )
            .set_thumbnail(url=self.bot.user.display_avatar.url)
        )

        await ctx.safe_send(embed=embed)

    @commands.group(
        name="emoji",
        aliases=("emote", "emotes", "emojis"),
        invoke_without_command=True,
    )
    async def emoji(
        self,
        ctx: Context,
        *,
        emojis: Optional[list[discord.PartialEmoji]] = commands.param(
            default=None,
            converter=EmojiConverter(),
            displayed_default="Message history or reference",
        ),
    ) -> None:
        if not emojis:
            maybe_emojis: list[discord.PartialEmoji] | None = await EmojiConverter().convert(
                ctx, None
            )

            if maybe_emojis:
                emojis = maybe_emojis
            else:
                raise UserFeedbackExceptionFactory.create(
                    message="No emotes found in the message.",
                    level=ExceptionLevel.INFO,
                )

        items: list[EmoteUnit] = [
            EmoteUnit(
                name=emoji.name,
                id=emoji.id or int(hex(id(emoji))[2:], 16),
                emote=emoji,
            )
            for emoji in emojis
        ]

        await EmoteView(self.bot, *items).send_to_ctx(ctx)

    @emoji.group(name="set", aliases=("add",), invoke_without_command=True)
    async def emoji_set(self, ctx: Context) -> None:
        await ctx.send_help()

    @emoji_set.command(name="guild", aliases=("server", "g", "s"))
    async def emoji_set_guild(self, ctx: Context) -> None:
        if not isinstance(ctx.author, discord.Member):
            # Purely for type checking, the cog_check above already
            # ensures that this is a guild only command.
            return

        if not ctx.author.guild_permissions.manage_emojis:
            raise UserFeedbackExceptionFactory.create(
                message="You don't have the required permissions to use this command.",
                level=ExceptionLevel.WARNING,
            )
        if not ctx.guild.me.guild_permissions.manage_emojis:
            raise UserFeedbackExceptionFactory.create(
                message="I don't have the required permissions to use this command.",
                level=ExceptionLevel.WARNING,
            )

        user: User | None = self.bot.cached_users.get(ctx.author.id)
        if user is None:
            user = await self.bot.manager.get_or_create_user(ctx.author.id)
            self.bot.cached_users[user.id] = user

        self.bot.cached_users[ctx.author.id] = await self.bot.manager.set_user_emoji_server(
            user, ctx.guild.id
        )

        await ctx.safe_send(f"Set your emoji server to `{ctx.guild.name}`.")

    @commands.has_guild_permissions(administrator=True)
    @commands.group(name="toggle", invoke_without_command=True)
    async def toggle(self, ctx: Context) -> None:
        await ctx.send_help()

    @toggle.command(name="counting")
    async def toggle_counting(self, ctx: Context) -> None:
        if (guild := self.bot.cached_guilds.get(ctx.guild.id)) is None:
            guild = await self.bot.manager.get_or_create_guild(ctx.guild.id)

        self.bot.cached_guilds[guild.id] = await self.bot.manager.toggle_guild_owo_counting(guild)

        true, false = "✅", "❌"
        await ctx.safe_send(
            f"**{true if self.bot.cached_guilds[guild.id].owo_counting else false} |** "
            f"counting has been "
            f"**{'enabled' if self.bot.cached_guilds[guild.id].owo_counting else 'disabled'}**."
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Managment(bot))

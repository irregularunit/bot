"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from discord.ext import commands

from models import EmbedBuilder
from utils import BaseExtension, async_all, for_all_callbacks, get_random_emoji

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("Managment",)

log: logging.Logger = logging.getLogger(__name__)


@for_all_callbacks(commands.cooldown(1, 3, commands.BucketType.user))
class Managment(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        checks = [commands.guild_only()]
        return await async_all(check(ctx) for check in checks)

    def compile_prefixes(self, prefixes: list[str]) -> re.Pattern[str]:
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
            self.compile_prefixes, self.bot.cached_guilds[ctx.guild.id].prefixes
        )

        await ctx.safe_send(f"Added `{prefix}` to the guild's prefixes.")

    @prefix.command(name="remove", aliases=("rm",))
    async def prefix_remove(self, ctx: Context, *, prefix: str) -> None:
        if (guild := self.bot.cached_guilds.get(ctx.guild.id)) is None:
            guild = await self.bot.manager.get_or_create_guild(ctx.guild.id)

        self.bot.cached_guilds[guild.id] = await self.bot.manager.remove_guild_prefix(guild, prefix)
        self.bot.cached_prefixes[ctx.guild.id] = await self.bot.to_thread(
            self.compile_prefixes, self.bot.cached_guilds[ctx.guild.id].prefixes
        )

        await ctx.safe_send(f"Removed `{prefix}` from the guild's prefixes.")

    @prefix.command(name="list", aliases=("ls",))
    async def prefix_list(self, ctx: Context) -> None:
        if (guild := self.bot.cached_guilds.get(ctx.guild.id)) is None:
            guild = await self.bot.manager.get_or_create_guild(ctx.guild.id)

        embed: EmbedBuilder = (
            EmbedBuilder()
            .set_author(name=f"{get_random_emoji()} Prefix settings for {ctx.guild.name}")
            .set_footer(text="Made with ❤️ by irregularunit.", icon_url=self.bot.user.display_avatar)
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


async def setup(bot: Bot) -> None:
    await bot.add_cog(Managment(bot))

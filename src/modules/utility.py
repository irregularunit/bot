"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, TypedDict

from discord.ext import commands

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory
from models.embed import EmbedBuilder
from utils import BaseExtension, async_all, for_all_callbacks, get_random_emoji

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("Utility",)

log: logging.Logger = logging.getLogger(__name__)


IP_LOOKUP_URL = "https://ipapi.co/{ip}/{format}/"
IP_REGEX = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
DOMAIN_REGEX = re.compile(
    r"^(([a-zA-Z]{1})|([a-zA-Z]{1}[a-zA-Z]{1})|([a-zA-Z]{1}[0-9]{1})|([0-9]{1}[a-zA-Z]{1})|"
    r"([a-zA-Z0-9][a-zA-Z0-9-_]{1,61}[a-zA-Z0-9]))\.([a-zA-Z]{2,6}|[a-zA-Z0-9-]{2,30}\.[a-zA-Z]{2,3})$"
)


class IPResponse(TypedDict):
    ip: str
    version: str
    city: str
    region: str
    region_code: str
    country: str
    country_name: str
    country_code: str
    country_code_iso3: str
    country_capital: str
    country_tld: str
    continent_code: str
    in_eu: bool
    postal: str
    latitude: float
    longitude: float
    timezone: str
    utc_offset: str
    country_calling_code: str
    currency: str
    currency_name: str
    languages: str
    country_area: float
    country_population: float
    asn: str
    org: str


@for_all_callbacks(commands.cooldown(1, 3, commands.BucketType.user))
class Utility(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    async def cog_check(self, ctx: Context) -> bool:  # skipcq: PYL-R0201
        checks = [commands.guild_only()]
        return await async_all(check(ctx) for check in checks)

    @commands.command(name="nslookup")
    async def nslookup(self, ctx: Context, *, domain: str) -> None:
        if not DOMAIN_REGEX.match(domain):
            raise UserFeedbackExceptionFactory.create(
                "Please provide a valid domain name.",
                ExceptionLevel.WARNING,
            )

        process = await asyncio.create_subprocess_shell(
            f"nslookup {domain}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            await ctx.safe_send(f"```{stdout.decode()}```")
        elif stderr:
            await ctx.safe_send(f"```{stderr.decode()}```")

    @commands.command(name="iplookup")
    async def iplookup(self, ctx: Context, *, ip: str) -> None:
        if not IP_REGEX.match(ip):
            raise UserFeedbackExceptionFactory.create(
                "Please provide a valid IP address.",
                ExceptionLevel.WARNING,
            )

        async with self.bot.session.get(IP_LOOKUP_URL.format(ip=ip, format="json")) as resp:
            if resp.status != 200:
                raise UserFeedbackExceptionFactory.create(
                    "An error occurred while fetching the IP information.",
                    ExceptionLevel.WARNING,
                )

            js: IPResponse = await resp.json()

        fields = (
            ("IP", js["ip"], True),
            ("Version", js["version"], True),
            ("City", js["city"], True),
            ("Region", js["region"], True),
            ("Country Name", js["country_name"], True),
            ("Country Code", js["country_code"], True),
            ("Country Code (ISO3)", js["country_code_iso3"], True),
            ("Country Capital", js["country_capital"], True),
            ("Country TLD", js["country_tld"], True),
            ("Country Calling Code", js["country_calling_code"], True),
            ("Country Area", js["country_area"], True),
            ("Country Population", js["country_population"], True),
            ("Currency", js["currency"], True),
            ("Currency Name", js["currency_name"], True),
            ("Organization", js["org"], True),
        )

        embed: EmbedBuilder = EmbedBuilder.factory(
            ctx,
            title=f"{get_random_emoji()} IP Lookup Results",
            fields=fields,
        )

        await ctx.safe_send(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Utility(bot))

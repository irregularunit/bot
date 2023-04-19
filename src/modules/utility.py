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
import uuid
from typing import TYPE_CHECKING, TypedDict

import discord
from discord.ext import commands

from exceptions import ExceptionLevel, UserFeedbackExceptionFactory
from models.embed import EmbedBuilder
from utils import HTTP_STATUS_CODES, BaseExtension, async_all, for_all_callbacks, get_random_emoji

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
    """IP lookup response.

    Attributes
    ----------
    ip: `str`
        The IP address.
    version: `str`
        The IP version.
    city: `str`
        The city.
    region: `str`
        The region.
    region_code: `str`
        The region code.
    country: `str`
        The country.
    country_name: `str`
        The country name.
    country_code: `str`
        The country code.
    country_code_iso3: `str`
        The country code ISO3.
    country_capital: `str`
        The country capital.
    country_tld: `str`
        The country TLD.
    continent_code: `str`
        The continent code.
    in_eu: `bool`
        Whether the country is in the EU.
    postal: `str`
        The postal code.
    latitude: `float`
        The latitude.
    longitude: `float`
        The longitude.
    timezone: `str`
        The timezone.
    utc_offset: `str`
        The UTC offset.
    country_calling_code: `str`
        The country calling code.
    currency: `str`
        The currency.
    currency_name: `str`
        The currency name.
    languages: `str`
        The languages.
    country_area: `float`
        The country area.
    country_population: `float`
        The country population.
    asn: `str`
        The ASN.
    org: `str`
        The organization.
    """

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
    """Utility commands.

    Attributes
    ----------
    bot: `Bot`
        The bot instance.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    @property
    def emoji(self) -> str:
        """Get the emoji for the extension.

        Returns
        -------
        `str`
            The emoji for the extension.
        """
        return "\N{ELECTRIC LIGHT BULB}"

    async def cog_check(self, ctx: Context) -> bool:  # skipcq: PYL-R0201
        """Check if the command is guild only.

        Parameters
        ----------
        ctx: `Context`
            The context of the command.

        Returns
        -------
        `bool`
            Whether the command is guild only.
        """
        checks = [commands.guild_only()]
        return await async_all(check(ctx) for check in checks)

    @commands.command(name="nslookup")
    async def nslookup(self, ctx: Context, *, domain: str) -> None:
        if not DOMAIN_REGEX.match(domain):
            raise UserFeedbackExceptionFactory.create(
                "Please provide a valid domain name.",
                ExceptionLevel.INFO,
            )

        process = await asyncio.create_subprocess_shell(
            f"nslookup -query=any {domain}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            await ctx.safe_send(f"```{stdout.decode()[:len(stdout.decode()) - 43]}```")
        elif stderr:
            await ctx.safe_send(f"```{stderr.decode()}```")

    @commands.command(name="iplookup")
    async def iplookup(self, ctx: Context, *, ip: str) -> None:
        if not IP_REGEX.match(ip):
            raise UserFeedbackExceptionFactory.create(
                "Please provide a valid IP address.",
                ExceptionLevel.INFO,
            )

        async with self.bot.session.get(IP_LOOKUP_URL.format(ip=ip, format="json")) as resp:
            if resp.status != 200:
                raise UserFeedbackExceptionFactory.create(
                    "An error occurred while fetching the IP information.",
                    ExceptionLevel.WARNING,
                )

            js: IPResponse = await resp.json()

            embed: EmbedBuilder = EmbedBuilder.factory(
                ctx,
                title=f"{get_random_emoji()} IP Lookup Results",
                fields=(
                    ("IP", js["ip"], True),
                    ("Version", js["version"], True),
                    ("City", js["city"], True),
                    ("Region", js["region"], True),
                    ("Country Name", js["country_name"], True),
                    ("Country Code (ISO3)", js["country_code_iso3"], True),
                    ("Country TLD", js["country_tld"], True),
                    ("Country Calling Code", js["country_calling_code"], True),
                    ("Country Population", js["country_population"], True),
                    ("Currency", js["currency"], True),
                    ("Currency Name", js["currency_name"], True),
                    ("Organization", js["org"], True),
                ),
            )

            await ctx.send(embed=embed)

    @commands.command(name="password", aliases=("pass",))
    async def password(self, ctx: Context, *, length: int = 16) -> None:
        if not 8 <= length <= 32:
            raise UserFeedbackExceptionFactory.create(
                "Please provide a length between 8 and 32.",
                ExceptionLevel.INFO,
            )

        password: str = uuid.uuid4().hex[:length]

        embed: EmbedBuilder = EmbedBuilder.factory(
            ctx,
            title=f"{get_random_emoji()} Password Generator",
            description=f"Your password is: `{password}`",
        )

        await ctx.author.send(embed=embed)

        try:
            await ctx.message.add_reaction("✅")
        except (discord.HTTPException,):
            pass

    @commands.command(name="httpstatus", aliases=("http",))
    async def httpstatus(self, ctx: Context, *, status_code: int) -> None:
        if status_code not in HTTP_STATUS_CODES:
            status_code = 404

        HTTP_CAT_URL: str = f"https://http.cat/{status_code}"

        async with self.bot.session.get(HTTP_CAT_URL) as resp:
            if resp.status != 200:
                raise UserFeedbackExceptionFactory.create(
                    "An error occurred while fetching the HTTP status code.",
                    ExceptionLevel.WARNING,
                )

            embed: EmbedBuilder = EmbedBuilder.factory(
                ctx,
                title=f"{get_random_emoji()} HTTP Status Code",
                description=f"`Code ID  :` `{status_code}`",
            )

            embed.set_image(url=HTTP_CAT_URL)

            await ctx.send(embed=embed)

    @commands.command(name="nmap")
    async def nmap(self, ctx: Context, host: str) -> None:
        if not DOMAIN_REGEX.match(host):
            raise UserFeedbackExceptionFactory.create(
                "Please provide a valid domain name.",
                ExceptionLevel.INFO,
            )

        process = await asyncio.create_subprocess_shell(
            f"nmap {host}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            await ctx.safe_send(f"```{stdout.decode()}```")
        elif stderr:
            await ctx.safe_send(f"```{stderr.decode()}```")


async def setup(bot: Bot) -> None:
    """Load the Utility cog.

    Parameters
    ----------
    bot: `Bot`
        The bot instance.
    """
    await bot.add_cog(Utility(bot))

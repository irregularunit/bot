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

from collections import deque
from logging import Logger, getLogger
from typing import AbstractSet, Any, Generator, Type

import discord
from pydantic import BaseSettings
from pydantic.fields import ModelField
from typing_extensions import override

__all__: tuple[str, ...] = ("SerenityConfig",)

_logger: Logger = getLogger(__name__)
GeneratorType: Type[Generator[int, None, None]] = type(1 for _ in range(1))


class SerenityConfig(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    HOST: str
    PORT: int
    POSTGRES_DB: str

    DISCORD_TOKEN: str
    OWNER_IDS: list[int]
    TS_CHANNEL_ID: int

    LOG_LEVEL: str = "INFO"
    COLOR: int | discord.Colour = discord.Colour.dark_embed()
    CLIENT_USER: int = 1054123882384212078

    @property
    def sql_dsn(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@" f"{self.HOST}:{self.PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def invite(self) -> str:
        return discord.utils.oauth_url(
            client_id=self.CLIENT_USER,
            permissions=discord.Permissions(permissions=0x60E55FEE0),
            # View Channels
            # Manage Emojis and Stickers
            # Manage Webhooks
            # Send Messages
            # Send Messages in Threads
            # Embed Links
            # Attach Files
            # Add Reactions
            # Use External Emojis
            # Use External Stickers
            # Manage Messages
            # Read Message History
            # Use Application Commands
            scopes=("bot", "applications.commands"),
        )

    class Config(BaseSettings.Config):
        env_file = ".env"
        env_file_encoding = "utf-8"
        allow_mutation = False

        @staticmethod
        def _sequence_like(value: Any) -> bool:
            return isinstance(value, (list, tuple, set, frozenset, GeneratorType, deque))

        @override
        @classmethod
        def prepare_field(cls, field: ModelField) -> None:
            env_names: list[str] | AbstractSet[str]

            field_info_from_config: dict[str,
                                         Any] = cls.get_field_info(field.name)
            env: Any | None = field_info_from_config.get(
                "env") or field.field_info.extra.get("env")
            if env is None:
                if field.has_alias:
                    _logger.warning(
                        "No env name set for field %s, using alias %s",
                        field.name,
                        field.alias,
                    )
                env_names = {cls.env_prefix + field.name}
            elif isinstance(env, str):
                env_names = {env}
            elif isinstance(env, (set, frozenset)):
                env_names = env
            elif cls._sequence_like(env):
                env_names = list(env)
            else:
                raise TypeError(
                    f"Invalid field env type {type(env)} for field {field.name}")

            if not cls.case_sensitive:
                env_names = env_names.__class__(n.lower() for n in env_names)
            field.field_info.extra["env_names"] = env_names

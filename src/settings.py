from collections import deque
from logging import Logger, getLogger
from typing import AbstractSet, Any, Generator, Type

import discord
from pydantic import BaseSettings
from pydantic.fields import ModelField

__all__: tuple[str, ...] = ("Config",)


log: Logger = getLogger(__name__)

GeneratorType: Type[Generator[int, None, None]] = type(1 for _ in range(1))


class Config(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    token: str
    owner_ids: list[int]
    log_level: str = "INFO"
    client_user: int = 1054123882384212078

    # shamelessly stolen from
    # https://htmlcolorcodes.com/colors/shades-of-blue/
    color: int = 0x0096FF

    @property
    def psql(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def invite(self) -> str:
        return discord.utils.oauth_url(
            client_id=self.client_user,
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

        @classmethod
        def prepare_field(cls, field: ModelField) -> None:
            env_names: list[str] | AbstractSet[str]

            field_info_from_config: dict[str, Any] = cls.get_field_info(field.name)
            env: Any | None = field_info_from_config.get("env") or field.field_info.extra.get("env")
            if env is None:
                if field.has_alias:
                    log.warning(
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
                raise TypeError(f"Invalid field env type {type(env)} for field {field.name}")

            if not cls.case_sensitive:
                env_names = env_names.__class__(n.lower() for n in env_names)
            field.field_info.extra["env_names"] = env_names

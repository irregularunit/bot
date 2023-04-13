"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Iterable, Optional, Self, Type

from discord import Colour, Embed, Member, Message, User
from typing_extensions import override

from settings import Config

if TYPE_CHECKING:
    from datetime import datetime

    from src.utils import Context

__all__: tuple[str, ...] = ("EmbedBuilder",)
config: Config = Config()  # type: ignore


class EmbedBuilder(Embed):
    @override
    def __init__(
        self,
        *,
        colour: Optional[Colour | int] = config.color,
        timestamp: Optional[datetime] = None,
        fields: Iterable[tuple[str, str, bool]] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(colour=colour, timestamp=timestamp, **kwargs)
        for name, value, inline in fields:
            self.add_field(name=name, value=value, inline=inline)

    @classmethod
    def to_factory(cls: Type[Self], embed: Embed, **kwargs: Any) -> Self:
        setattr(kwargs, "colour", config.color)
        instance = cls(**kwargs)

        for key, value in embed.to_dict().items():
            if key in ("colour", "color"):
                continue

            setattr(instance, key, value)

        return instance

    @classmethod
    def from_message(
        cls: Type[Self],
        message: Message,
        **kwargs: Any,
    ) -> Self:
        if embeds := message.embeds:
            return cls.to_factory(embeds[0], **kwargs)

        author: User | Member = message.author
        instance = cls(**kwargs)

        instance.description = message.content
        instance.set_author(name=author.display_name, icon_url=author.display_avatar)

        if (
            message.attachments
            and message.attachments[0].content_type
            and message.attachments[0].content_type.startswith("image")
        ):
            instance.set_image(url=message.attachments[0].url)

        return instance

    @classmethod
    def from_action(cls: Type[Self], *, title: str, gif: str, footer: Optional[str] = None) -> Self:
        instance: Self = cls(title=title).set_image(url=gif)
        if footer:
            instance.set_footer(text=footer)

        return instance

    @classmethod
    def factory(cls: Type[Self], ctx: Context, **kwargs: Any) -> Self:
        instance = cls(**kwargs)
        instance.set_footer(
            text="Made with ❤️ by irregularunit.",
            icon_url=ctx.bot.user.display_avatar,
        )
        return instance

    def build(self) -> Embed:
        return copy.copy(self)

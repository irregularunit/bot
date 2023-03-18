from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Optional, Self, Type

from discord import Colour, Embed, Member, Message, User

if TYPE_CHECKING:
    from datetime import datetime

    from src.utils import Context

__all__: tuple[str, ...] = ("EmbedBuilder",)


class EmbedBuilder(Embed):
    def __init__(
        self,
        *,
        colour: Optional[Colour | int] = 0xF8B695,
        timestamp: Optional[datetime] = None,
        fields: Iterable[tuple[str, str, bool]] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(colour=colour, timestamp=timestamp, **kwargs)
        for name, value, inline in fields:
            self.add_field(name=name, value=value, inline=inline)

    @classmethod
    def to_factory(cls: Type[Self], embed: Embed, **kwargs: Any) -> Self:
        instance = cls(**kwargs)
        for key, value in embed.to_dict().items():
            setattr(instance, key, value)

        instance._colour = kwargs.get("colour", 0xF8B695)

        return instance

    @classmethod
    def from_message(
        cls: Type[Self],
        message: Message,
        *,
        fields: Iterable[tuple[str, str, bool]] = (),
        **kwargs: Any,
    ) -> Self:
        if embeds := message.embeds:
            # Change the appearance to match our embeds
            return cls.to_factory(embeds[0], **kwargs)

        author: User | Member = message.author
        instance = cls(**kwargs, fields=fields)

        instance.description = message.content
        instance.set_author(name=author.display_name, icon_url=author.display_avatar)

        if message.attachments and message.attachments[0].content_type:
            if message.attachments[0].content_type.startswith("image"):
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
        instance.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar)
        return instance

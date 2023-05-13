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

from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, Any, Iterable, Optional, Self, Type

from discord import Colour, Embed, Message
from typing_extensions import override

if TYPE_CHECKING:
    from datetime import datetime

    from src.models.discord import SerenityContext

__all__: tuple[str, ...] = ("SerenityEmbed",)


class SerenityEmbed(Embed):
    """A custom embed class for Serenity."""

    @override
    def __init__(
        self,
        *,
        colour: Optional[Colour] = Colour.dark_embed(),
        timestamp: Optional[datetime] = None,
        fields: Iterable[tuple[str, Any, bool]] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(colour=colour, timestamp=timestamp, **kwargs)

        self.description: str = kwargs.get("description", "")

        for name, value, inline in fields:
            self.add_field(name=name, value=value, inline=inline)

    @classmethod
    def _to_factory(cls: Type[Self], embed: Embed, **kwargs: Any) -> Self:
        """An internal method to copy an embed and return a new instance."""
        copied = copy(embed)
        copied.colour = Colour.dark_embed()

        return cls.from_dict(copied.to_dict(), **kwargs)

    @classmethod
    def from_message(
        cls: Type[Self],
        message: Message,
        **kwargs: Any,
    ) -> Self:
        """Create an embed from a message.

        This method will attempt to create an embed from the message's embeds
        first, and if that fails, it will create an embed from the message's
        content and attachments.

        Parameters
        ----------
        message: `discord.Message`
            The message to create an embed from.
        kwargs: `typing.Any`
            The keyword arguments to pass to the embed constructor.

        Returns
        -------
        `SerenityEmbed`
            The embed created from the message.
        """
        if embeds := message.embeds:
            return cls._to_factory(embeds[0], **kwargs)

        author = message.author
        instance = cls(**kwargs)

        instance.set_author(
            name=author.display_name,
            icon_url=author.display_avatar.url,
        )
        instance.description = message.content

        if message.attachments and message.attachments[0].content_type in (
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
        ):
            instance.set_image(url=message.attachments[0].url)

        return instance

    @classmethod
    def from_action(
        cls: Type[Self],
        *,
        title: str,
        gif: str,
        footer: Optional[str] = None,
    ) -> Self:
        """Create an embed from an action.

        Parameters
        ----------
        title: `str`
            The action's respective title.
        gif: `str`
            The action's bound gif.
        footer: `Optional[str]`
            May be provided to set the embed's footer.

        Returns
        -------
        `SerenityEmbed`
            The embed created from the action.
        """
        instance = cls(title=title).set_image(url=gif)

        if footer is not None:
            instance.set_footer(text=footer)

        return instance

    @classmethod
    def factory(cls: Type[Self], ctx: SerenityContext, **kwargs: Any) -> Self:
        """Create an embed from a context.

        Parameters
        ----------
        ctx: `SerenityContext`
            The context to create an embed from.
        kwargs: `typing.Any`
            The keyword arguments to pass to the embed constructor.

        Returns
        -------
        `SerenityEmbed`
            The embed created from the context.
        """
        instance = cls(**kwargs)

        instance.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url,
        )

        return instance

    def build(self) -> Self:
        """Returns a shallow copy of the embed."""
        return self.copy()

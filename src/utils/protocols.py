from typing import Any, Optional, Protocol, Sequence, Union, overload, runtime_checkable

from discord import (
    AllowedMentions,
    Embed,
    File,
    Guild,
    GuildSticker,
    Message,
    MessageReference,
    PartialMessage,
    StickerItem,
)
from discord.ui import View

__all__: tuple[str, ...] = ("GuildMessageable",)


@runtime_checkable
class GuildMessageable(Protocol):
    """A protocol for a messageable object that is in a guild.

    Attributes
    ----------
    `guild`
        The guild that the messageable object is in.

    Methods
    -------
    `send()`
        Send a message to the messageable object.
    """

    guild: Guild

    @overload
    async def send(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embed: Embed = ...,
        file: File = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
    ) -> Message:
        ...

    @overload
    async def send(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embed: Embed = ...,
        files: Sequence[File] = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
    ) -> Message:
        ...

    @overload
    async def send(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[Embed] = ...,
        file: File = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
    ) -> Message:
        ...

    @overload
    async def send(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[Embed] = ...,
        files: Sequence[File] = ...,
        stickers: Sequence[Union[GuildSticker, StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
        view: View = ...,
        suppress_embeds: bool = ...,
    ) -> Message:
        ...

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        """Send a message to the messageable object.

        Parameters
        ----------
        content: :class:`str`
            The content of the message.
        tts: :class:`bool`
            Whether the message should be sent using text-to-speech.
        embed: :class:`Embed`
            The embed to be sent.
        embeds: :class:`list[Embed]`
            A list of embeds to be sent.
        file: :class:`File`
            The file to be sent.
        files: :class:`list[File]`
            A list of files to be sent.

        Returns
        -------
        :class:`Message`
            The message that was sent. Assuming OK, since this is a protocol.
        """

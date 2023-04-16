"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import uuid
from io import BytesIO
from logging import Logger, getLogger
from typing import NamedTuple

from discord import File
from PIL import Image

__all__: tuple[str, ...] = ("AvatarCollage", "AvatarCollageType")


logger: Logger = getLogger("avatar-collage")


class AvatarCollageType(NamedTuple):
    """AvatarCollageType is a type hint for the avatar collage data.

    Parameters
    ----------
    avatar : `bytes`
        The avatar of the user.
    avatars : `list[bytes]`
        The avatars of the user.
    """

    avatars: list[Image.Image]

    def grid_size(self) -> int:
        """Compute the grid size for the collage.

        Returns
        -------
        `int`
            The grid size.
        """
        amount: int = len(self.avatars)
        return int(amount**0.5) + 1 if amount**0.5 % 1 else int(amount**0.5)


class AvatarCollage:
    """AvatarCollage is a class that generates an avatar collage.

    Parameters
    ----------
    avatar_collage : `AvatarCollageType`
        The avatar collage data.

    Attributes
    ----------
    id : `str`
        The ID of the avatar collage.
    """

    def __init__(self, collage: AvatarCollageType) -> None:
        self.id: str = str(uuid.uuid4())
        self.collage: AvatarCollageType = collage

        self.grid_size: int = self.collage.grid_size()
        self.width = self.height = 256 * self.grid_size
        self.x = self.y = 0

        self.image: Image.Image

    def create(self) -> File:
        """Create a collage of the user's avatars.

        Returns
        -------
        `Optional[File]`
            The BytesIO object containing the image.
        """
        with Image.new("RGBA", (self.width, self.height)) as self.image:
            self.draw_collage()
            buffer: BytesIO = BytesIO()
            self.image.save(buffer, "webp")
            buffer.seek(0)
            return File(buffer, filename=f"{self.id}.webp")

    def draw_collage(self) -> None:
        """Draw the collage."""
        fx = fy = 0
        for avatar in self.collage.avatars:
            if self.x == self.grid_size:
                self.y += 1
                self.x = 0

            x, y = self.x * 256, self.y * 256
            self.image.paste(avatar, (x, y))

            fx, fy = max(x, fx), max(y, fy)
            self.x += 1

        self.image: Image.Image = self.image.crop((0, 0, fx + 256, fy + 256))

    def save(self) -> None:
        """Save the avatar collage to the disk."""
        self.image.save(f"{self.id}.png")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"

    def __str__(self) -> str:
        return self.__repr__()

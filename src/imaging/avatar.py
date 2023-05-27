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

from asyncio import to_thread
from copy import deepcopy
from io import BytesIO
from logging import getLogger
from pathlib import Path
from typing import Generator
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from .abc import SavableByteStream

__all__: tuple[str, ...] = ("AvatarPointer", "FilePointer", "AvatarCollage")

_logger = getLogger(__name__)
_ROOT = Path("images")


class FilePointer:
    __slots__: tuple[str, ...] = ("uid", "root")

    uid: int
    root: Path

    def __init__(self, uid: int) -> None:
        self.uid = uid
        self.root = _ROOT

    @property
    def empty(self) -> bool:
        return not bool(len(self))

    @property
    def current_path(self) -> Path:
        return self.root / str(self.uid)

    def __iter__(self) -> Generator[Image.Image, None, None]:
        for file in sorted(self.current_path.iterdir(), key=lambda x: x.stat().st_mtime):
            yield Image.open(file)

    def __len__(self) -> int:
        return len(list(self.current_path.iterdir())) if self.current_path.exists() else 0

    def __repr__(self) -> str:
        return f"<Files uid={self.uid} length={len(self)}>"

    def __str__(self) -> str:
        return repr(self)


class AvatarPointer:
    __slots__: tuple[str, ...] = (
        "_uid",
        "_name",
        "_mime_type",
        "_file",
        "root",
    )

    root: Path
    _uid: int
    _mime_type: str
    _file: BytesIO

    def __init__(
        self,
        uid: int,
        mime_type: str,
        *,
        file: BytesIO,
    ) -> None:
        self._uid = uid
        self._mime_type = mime_type
        self._file = file

        self.root = _ROOT

    def __repr__(self) -> str:
        return f"<AvatarPointer uid={self.uid}>"

    @property
    def uid(self) -> int:
        return self._uid

    @property
    def content_type(self) -> str:
        return self._mime_type

    @property
    def file(self) -> BytesIO:
        """Returns a copy of the Image for reusability."""
        return deepcopy(self._file)

    @property
    def current_path(self) -> Path:
        return self.root / str(self.uid)

    def _save_to_path(self) -> None:
        if not self.root.exists():
            self.root.mkdir()

        if not self.current_path.exists():
            self.current_path.mkdir()

        try:
            with Image.open(self._file) as image:
                image = image.resize((256, 256))
                image = image.resize((256, 256))
                hash_new = hash(image.tobytes())  # type: ignore
        except UnidentifiedImageError:
            _logger.warning("Unable to open %s's file pointer.", self.uid)
            return

        path_files = list(self.current_path.iterdir())
        hashes: set[int] = set()

        for file in path_files:
            with Image.open(file) as _copy:
                hashes.add(hash(_copy.tobytes()))  # type: ignore

        # Saves us some space. :)
        if hash_new in hashes:
            return

        if len(path_files) >= 100:
            oldest = min(path_files, key=lambda x: x.stat().st_mtime)
            oldest.unlink()

        destination = self.current_path / f"{uuid4().hex}.png"
        with destination.open("wb") as file:
            image.save(file, format="PNG")

    async def save(self) -> None:
        await to_thread(self._save_to_path)


class AvatarCollage(SavableByteStream):
    __slots__: tuple[str, ...] = ("_pointer", "x", "y")

    x: int
    y: int
    _pointer: FilePointer

    def __init__(self, pointer: FilePointer) -> None:
        self._pointer = pointer
        self.x = self.y = 0

    @property
    def images(self) -> list[Image.Image]:
        return list(self._pointer)

    def _get_grid_size(self) -> int:
        amount = len(self._pointer)
        return int(amount**0.5) + 1 if amount**0.5 % 1 else int(amount**0.5)

    def _create_collage(self) -> Image.Image:
        size = self._get_grid_size()
        width = height = size * 256

        with Image.new("RGBA", (width, height)) as canvas:
            fx = fy = 0

            for avatar in self._pointer:
                if self.x == size:
                    self.y += 1
                    self.x = 0

                x, y = self.x * 256, self.y * 256
                canvas.paste(avatar, (x, y))

                fx = max(x, fx)
                fy = max(y, fy)

                self.x += 1

            return canvas.crop((0, 0, fx + 256, fy + 256))

    async def buffer(self) -> BytesIO:
        """Returns a BytesIO object of the image."""
        buffer = BytesIO()
        canvas = await to_thread(self._create_collage)

        canvas.save(buffer, "PNG")
        buffer.seek(0)

        return buffer

    def __repr__(self) -> str:
        return f"<Collage uid={self._pointer.uid} length={len(self._pointer)}>"

    def __str__(self) -> str:
        return repr(self)

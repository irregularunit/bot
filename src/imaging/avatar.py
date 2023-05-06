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

# pyright: reportMissingTypeStubs=false
import numpy as np
from PIL import Image, UnidentifiedImageError
from skimage.metrics import structural_similarity as ssim  # type: ignore

__all__: tuple[str, ...] = ("AvatarPointer", "FilePointer", "AvatarCollage")

_logger = getLogger(__name__)
_ROOT = Path("images")


class AvatarPointer:
    __slots__: tuple[str, ...] = (
        "_uid",
        "_name",
        "_mime_type",
        "_file",
        "root",
    )

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

        if not (self.root / str(self.uid)).exists():
            (self.root / str(self.uid)).mkdir()

        try:
            image = Image.open(self._file)
        except UnidentifiedImageError:
            _logger.warning("Unable to open %s's file pointer.", self.uid)
            return

        image = image.resize((256, 256))

        for file in self.current_path.iterdir():
            # Saves us some space. :)
            if self._is_simmilar(image, Image.open(file)):
                return
        
        # Removes the oldest file if there are more than 100.
        if len(list(self.current_path.iterdir())) >= 100:
            oldest = min(self.current_path.iterdir(), key=lambda x: x.stat().st_mtime)
            oldest.unlink()

        image.save(
            fp=self.current_path / f"{uuid4().hex}.png",
            format=image.format,
        )

    def _is_simmilar(self, original: Image.Image, other: Image.Image) -> bool:
        """Checks if the image is simmilar to the one we're saving."""
        ifloat1 = np.asarray(original.convert("L")).astype("float")
        ifloat2 = np.asarray(other.convert("L")).astype("float")

        mse = np.mean((ifloat1 - ifloat2) ** 2)
        mse /= float(ifloat1.shape[0] * ifloat1.shape[1])

        ssim_score: float = ssim(
            ifloat1, ifloat2, data_range=ifloat2.max() - ifloat2.min()  # type: ignore
        )

        return mse < 100 and ssim_score > 0.9  # type: ignore

    async def save(self) -> None:
        """Saves the file to the disk."""
        await to_thread(self._save_to_path)


class FilePointer:
    __slots__: tuple[str, ...] = ("uid", "root")

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


class AvatarCollage:
    __slots__: tuple[str, ...] = ("_pointer", "x", "y")

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

                (
                    fx,
                    fy,
                ) = max(
                    x, fx
                ), max(y, fy)
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

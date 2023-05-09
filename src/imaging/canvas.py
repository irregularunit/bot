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
# pyright: reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false

from __future__ import annotations

from asyncio import to_thread
from io import BytesIO
from uuid import uuid4
from typing import List, Optional

import numpy as np
from discord import File
from PIL import Image, ImageDraw, ImageFont
from skimage.color import rgb2gray  # type: ignore


from .utils import rgb_to_hex


__all__: tuple[str, ...] = ("Canvas",)


class Canvas:
    """A class with methods for manipulating images.

    Attributes
    ----------
    image: `bytes`
        The image to manipulate.
    """


    def __init__(self, image: bytes) -> None:
        self.image = image
        self.bebas = ImageFont.truetype("static/fonts/BEBAS.ttf", 28)

    def _mock_size(self, image: Image.Image, size: int) -> Image.Image:
        if image.width > image.height:
            new_width = size
            new_height = int((new_width / image.width) * image.height)
        else:
            new_height = size
            new_width = int((new_height / image.height) * image.width)

        return image.resize((new_width, new_height), Image.ANTIALIAS)

    def _to_discord_file(self, buffer: BytesIO) -> File:
        return File(buffer, filename=f"{uuid4()}.png")

    def _create_pallete_canvas(self) -> BytesIO:
        with Image.open(BytesIO(self.image)) as canvas:
            width, height = canvas.size
            canvas = self._mock_size(canvas, 256)

            quantized = canvas.quantize(colors=5, method=2)
            palette = quantized.getpalette()

            if not palette:
                buffer = BytesIO()
                canvas.save(buffer, format="PNG")
                buffer.seek(0)
                return buffer

            with Image.new(
                "RGBA", (int(width * (256 / height)) + 200, 256), color=(0, 0, 0, 0)
            ) as background:
                draw = ImageDraw.Draw(background)
                text_color = (255, 255, 255)

                for i in range(5):
                    x1, y1, x2, y2 = 10, 10 + (i * 50), 40, 40 + (i * 50)

                    color = (palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2])
                    draw.rectangle((x1, y1, x2, y2), fill=color, outline=text_color)

                    text_position = (x2 + 10, y1 - 4)
                    draw.text(  # type: ignore
                        text_position,
                        f"{rgb_to_hex(color)}",
                        font=self.bebas,
                        fill=text_color,
                    )

                background.paste(canvas, (200, 0))

                buffer = BytesIO()
                background.save(buffer, format="PNG")
                buffer.seek(0)

                return buffer

    async def to_pallete(self) -> File:
        """Return the avatar as a pallete."""
        buffer = await to_thread(self._create_pallete_canvas)
        return self._to_discord_file(buffer)

    def _create_ascii_canvas(
        self,
        char_list: Optional[List[str]] = None,
        scale_factor: float = 0.1,
        gamma: float = 2.0,
        background: tuple[int, ...] = (0, 0, 0),
    ) -> BytesIO:
        if char_list is None:
            char_list = list(
                r"$@B%8&WM#*oahkbdpqwmZO0QLCJYXzcvunxrjft/\|()1{}[]?-+~<>i!lI;:,^`'."
            )

        with Image.open(BytesIO(self.image)).convert("RGB") as canvas:
            canvas = self._mock_size(canvas, 512)
            image: np.ndarray[np.float64, np.dtype[np.float64]] = rgb2gray(np.array(canvas))

            box = ImageFont.load_default().getbbox("x")  # type: ignore
            char_width: int = box[2] - box[0] 
            char_height: int = box[3] - box[1]

            width_by_char = round(image.shape[1] * scale_factor)
            height_by_char = round(
                image.shape[0] * scale_factor * char_width / char_height
            )

            image = np.power(image, gamma)
            image = (
                (image - image.min()) 
                / (image.max() - image.min())
                * (len(char_list) - 1)
            )
            image = image.astype(int)

            lines: list[str] = []
            for i in range(height_by_char):
                line = ""
                for j in range(width_by_char):
                    try:
                        line += char_list[
                            image[
                                round(i * image.shape[0] / height_by_char),
                                round(j * image.shape[1] / width_by_char),
                            ]
                        ]
                    except IndexError:
                        line += " "
                lines.append(line)

            new_image_width: int = width_by_char * char_width
            new_image_height: int = height_by_char * char_height

            with Image.new(
                "RGBA", (new_image_width, new_image_height), background
            ) as bg:
                draw = ImageDraw.Draw(bg)

                for i, line in enumerate(lines):
                    neon_green_color = (57, 255, 20)
                    draw.text((0, i * char_height), line, fill=neon_green_color)

                buffer = BytesIO()
                bg.save(buffer, format="PNG")
                buffer.seek(0)

                return buffer

    async def to_ascii(self) -> File:
        """Return the avatar as an ASCII image."""
        buffer = await to_thread(self._create_ascii_canvas)
        return self._to_discord_file(buffer)

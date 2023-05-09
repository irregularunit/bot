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
from typing import Optional
from uuid import uuid4

import numpy as np
from discord import File
from PIL import Image, ImageDraw, ImageFont

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

            quantized = canvas.quantize(colors=6, method=2)
            palette = quantized.getpalette()

            if not palette:
                buffer = BytesIO()
                canvas.save(buffer, format="PNG")
                buffer.seek(0)
                return buffer

            if palette[:3] == [0, 0, 0]:
                palette = palette[3:]

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
        ascii_chars: Optional[np.ndarray] = None,  # type: ignore
        scale: float = 0.1,
        gamma: float = 2.0,
        background: tuple[int, ...] = (13, 2, 8),
    ) -> BytesIO:
        with Image.open(BytesIO(self.image)) as image:
            image = self._mock_size(image, 1024)
            image_scaled = np.array(
                image.convert("RGB").resize(
                    (int(scale * image.width), int(scale * image.height))
                )
            )

        if not ascii_chars:
            ascii_chars = np.asarray(
                list(
                    r" .'`^\,:;Il!i><~+_-?][}{1)(|\/tfjrxn"
                    r"uvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
                )
            )

        font = ImageFont.load_default()
        letter_width, letter_height = font.getsize("x")
        wcf = letter_height / letter_width

        width_in_chars = round(image_scaled.shape[1] * wcf)
        height_in_chars = round(image_scaled.shape[0])
        image_sum = np.sum(image_scaled, axis=2)
        image_sum -= image_sum.min()
        image_normalized = (1.0 - image_sum / image_sum.max()) ** gamma * (
            len(ascii_chars) - 1
        )

        ascii_image = np.array([ascii_chars[i] for i in image_normalized.astype(int)])
        lines = "\n".join(["".join(row) for row in ascii_image])

        new_img_width = letter_width * width_in_chars
        new_img_height = letter_height * height_in_chars

        with Image.new("RGBA", (new_img_width, new_img_height), background) as new_img:
            draw = ImageDraw.Draw(new_img)
            y = 0

            for line in lines.split("\n"):
                draw.text((0, y), line, (0, 255, 65), font=font)
                y += letter_height

            left_area = (0, 0, new_img_width // 2, new_img_height)
            new_img = new_img.crop(left_area)
            new_img = new_img.resize((512, 512), Image.ANTIALIAS)

            buffer = BytesIO()
            new_img.save(buffer, format="PNG")
            buffer.seek(0)

            return buffer

    async def to_ascii(self) -> File:
        """Return the avatar as an ASCII image."""
        buffer = await to_thread(self._create_ascii_canvas)
        return self._to_discord_file(buffer)

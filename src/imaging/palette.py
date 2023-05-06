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

from io import BytesIO
from asyncio import to_thread

from PIL import Image, ImageDraw, ImageFont

from .utils import rgb_to_hex


__all__: tuple[str, ...] = ("AvatarPallete",)



class AvatarPallete:
    def __init__(self, avatar: bytes) -> None:
        self.avatar = avatar
        self.font = ImageFont.truetype("static/fonts/BEBAS.ttf", 28)

    def _create_pallete(self) -> BytesIO:
        with Image.open(BytesIO(self.avatar)) as canvas:
            width, height = canvas.size

            if height != 256:
                canvas = canvas.resize((int(width * (256 / height)), 256), 1)

            quantized = canvas.quantize(colors=5, method=2)
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

                    color = (palette[i*3], palette[i*3+1], palette[i*3+2])
                    draw.rectangle((x1, y1, x2, y2), fill=color, outline=text_color)

                    text_position = (x2 + 10, y1 - 4)
                    draw.text(  # type: ignore
                        text_position,
                        f"{rgb_to_hex(color)}",
                        font=self.font,
                        fill=text_color
                    ) 

                background.paste(canvas, (200, 0))

                buffer = BytesIO()
                background.save(buffer, format="PNG")
                buffer.seek(0)

                return buffer

    async def buffer(self) -> BytesIO:
        return await to_thread(self._create_pallete)

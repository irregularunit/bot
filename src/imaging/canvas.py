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
from enum import IntEnum
from io import BytesIO
from pathlib import Path
from random import randint
from typing import Any
from uuid import uuid4

import numpy as np
from discord import File
from PIL import Image, ImageDraw, ImageFont

from .utils import rgb_to_hex

__all__: tuple[str, ...] = ("Canvas", "CanvasOption")


class ImageManipulator:
    """A base class for image manipulation."""

    image: BytesIO

    def __init__(self, image: bytes) -> None:
        self.image = BytesIO(image)

    @staticmethod
    def resize(image: Image.Image, size: int) -> Image.Image:
        if image.width > image.height:
            new_width = size
            new_height = int((new_width / image.width) * image.height)
        else:
            new_height = size
            new_width = int((new_height / image.height) * image.width)

        return image.resize((new_width, new_height), Image.ANTIALIAS)

    @staticmethod
    def to_discord_file(buffer: BytesIO, fmt: str = "PNG") -> File:
        return File(buffer, filename=f"{uuid4()}.{fmt.lower()}")


class PalleteCreator(ImageManipulator):
    def __init__(self, image: bytes) -> None:
        super().__init__(image)

        self.bebas = ImageFont.truetype("static/fonts/BEBAS.ttf", 28)

    def _create_pallete_canvas(self) -> BytesIO:
        with Image.open(self.image) as canvas:
            width, height = canvas.size
            canvas = self.resize(canvas, 256)

            quantized = canvas.quantize(colors=6, method=2)
            palette = quantized.getpalette()

            if palette is None:
                buffer = BytesIO()
                canvas.save(buffer, format="PNG")
                buffer.seek(0)
                return buffer

            if palette[:3] == [0, 0, 0]:
                palette = palette[3:]

            with Image.new("RGBA", (int(width * (256 / height)) + 200, 256), color=(0, 0, 0, 0)) as background:
                draw = ImageDraw.Draw(background)
                text_color = (255, 255, 255)

                for i in range(5):
                    x1, y1, x2, y2 = 10, 10 + (i * 50), 40, 40 + (i * 50)

                    color = (palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2])
                    draw.rectangle((x1, y1, x2, y2), fill=color, outline=text_color)

                    text_position = (x2 + 10, y1 - 4)
                    draw.text(
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

        return self.to_discord_file(buffer)


class AsciiCreator(ImageManipulator):
    def __init__(self, image: bytes) -> None:
        super().__init__(image)
        self.ascii_chars = np.asarray(
            list(r" .'`^\,:;Il!i><~+_-?][}{1)(|\/tfjrxn" r"uvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$")
        )
        self.font = ImageFont.load_default()

    def _create_ascii_canvas(
        self,
        scale: float = 0.1,
        gamma: float = 2.0,
        background: tuple[int, ...] = (13, 2, 8),
    ) -> BytesIO:
        with Image.open(self.image) as image:
            image = self.resize(image, 1024)
            image_scaled = np.array(image.convert("RGB").resize((int(scale * image.width), int(scale * image.height))))

        letter_width, letter_height = self.font.getsize("x")
        wcf = letter_height / letter_width
        width_in_chars = round(image_scaled.shape[1] * wcf)
        height_in_chars = round(image_scaled.shape[0])
        image_sum = np.sum(image_scaled, axis=2)
        image_sum -= image_sum.min()
        image_normalized = (1.0 - image_sum / image_sum.max()) ** gamma * (len(self.ascii_chars) - 1)
        ascii_image = np.array([self.ascii_chars[i] for i in image_normalized.astype(int)])
        lines = "\n".join("".join(row) for row in ascii_image)
        new_img_width = letter_width * width_in_chars
        new_img_height = letter_height * height_in_chars

        with Image.new("RGBA", (new_img_width, new_img_height), background) as new_img:
            draw = ImageDraw.Draw(new_img)
            y = 0

            for line in lines.split("\n"):
                draw.text((0, y), line, (0, 255, 65), font=self.font)
                y += letter_height

            left_area = (0, 0, new_img_width // 2, new_img_height)
            new_img = new_img.crop(left_area)
            new_img = new_img.resize((512, 512), Image.ANTIALIAS)

            buffer = BytesIO()
            new_img.save(buffer, format="PNG")
            buffer.seek(0)

            return buffer

    async def to_ascii(self) -> File:
        buffer = await to_thread(self._create_ascii_canvas)

        return self.to_discord_file(buffer)


class PixelateCreator(ImageManipulator):
    def __init__(self, image: bytes) -> None:
        super().__init__(image)

    @staticmethod
    def shuffle(points: list[tuple[int, int]]) -> None:
        for i in range(len(points)):
            j = randint(0, len(points) - 1)
            points[i], points[j] = points[j], points[i]

    def _create_pixel_canvas(self) -> BytesIO:
        with Image.open(self.image) as canvas:
            canvas = self.resize(canvas, 512)

            with Image.new("RGBA", canvas.size, (0, 0, 0, 0)) as background:
                points = []

                for x in range(0, canvas.width, 10):
                    points.extend((x, y) for y in range(0, canvas.height, 10))
                self.shuffle(points)

                for point in points:
                    color = canvas.getpixel(point)
                    draw = ImageDraw.Draw(background)
                    draw.rectangle((point, (point[0] + 10, point[1] + 10)), fill=color)

                buffer = BytesIO()
                background.save(buffer, format="PNG")
                buffer.seek(0)

                return buffer

    async def to_pixel(self) -> File:
        buffer = await to_thread(self._create_pixel_canvas)

        return self.to_discord_file(buffer)


class TriggerCreator(ImageManipulator):
    def __init__(self, image: bytes) -> None:
        super().__init__(image)

        self.trigger_path = Path(__file__).parent / "images" / "triggered.png"

    def _create_triggered_canvas(self) -> BytesIO:
        with Image.open(self.image) as canvas:
            canvas = self.resize(canvas, 512)
            frames: list[Image.Image] = []

            square = 400, 400
            invisible = 0, 0, 0, 0
            red_colour = 255, 0, 0, 80

            for _ in range(30):
                with Image.new("RGBA", square, invisible) as layer:
                    x = -1 * randint(50, 100)
                    y = -1 * randint(50, 100)
                    layer.paste(canvas, (x, y))

                    with Image.new("RGBA", square, red_colour) as red:
                        layer.paste(red, mask=red)

                    with Image.open(self.trigger_path) as triggered:
                        layer.paste(triggered, mask=triggered)

                    frames.append(layer)

            initial_fram = frames[0]
            buffer = BytesIO()

            initial_fram.save(
                buffer,
                format="GIF",
                save_all=True,
                duration=60,
                loop=0,
                append_images=frames,
            )
            buffer.seek(0)

            return buffer

    async def to_triggerd(self) -> File:
        buffer = await to_thread(self._create_triggered_canvas)

        return self.to_discord_file(buffer, fmt="gif")


class PrideCreator(ImageManipulator):
    def __init__(self, image: bytes) -> None:
        super().__init__(image)

        self.size = (1024, 1024)

    @staticmethod
    def crop_avatar(avatar: Image.Image) -> Image.Image:
        with Image.new("L", avatar.size, 0) as mask:
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + avatar.size, fill=255)

            avatar.putalpha(mask)

            return avatar

    def crop_ring(self, ring: Image.Image, px: int) -> Image.Image:
        with Image.new("L", self.size, 0) as mask:
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + self.size, fill=255)
            draw.ellipse((px, px, self.size[0] - px, self.size[1] - px), fill=0)

            ring.putalpha(mask)

            return ring

    def prideavatar(self, option: str, pixels: int) -> BytesIO:
        pixels = max(0, min(512, pixels))
        option = option.lower()

        with Image.open(self.image) as avatar:
            avatar = avatar.convert("RGBA").resize(self.size)
            avatar = self.crop_avatar(avatar)

            with Image.open(Path("src", "imaging", "images", "pride", f"{option}.png")) as ring:
                ring = ring.convert("RGBA")
                ring = self.crop_ring(ring, pixels)
                avatar.alpha_composite(ring, (0, 0))

                buffer = BytesIO()
                avatar.save(buffer, format="PNG")
                buffer.seek(0)

                return buffer

    async def to_pride(self, option: str) -> File:
        buffer = await to_thread(self.prideavatar, option, 64)

        return self.to_discord_file(buffer)


class CanvasOption(IntEnum):
    ASCII = 0
    PALETTE = 1
    TRIGGER = 2
    PIXEL = 3
    PRIDE = 4


class Canvas(
    PalleteCreator,
    AsciiCreator,
    PixelateCreator,
    TriggerCreator,
    PrideCreator,
):
    def __init__(self, image: bytes) -> None:
        super().__init__(image)

        self.available_manipulators = {
            CanvasOption.ASCII: self.to_ascii,
            CanvasOption.PALETTE: self.to_pallete,
            CanvasOption.TRIGGER: self.to_triggerd,
            CanvasOption.PIXEL: self.to_pixel,
            CanvasOption.PRIDE: self.to_pride,
        }

    async def to_canvas(self, canvas_type: CanvasOption, **kwargs: Any) -> File:
        return await self.available_manipulators[canvas_type](**kwargs)

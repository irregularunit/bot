"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import uuid
from io import BytesIO
from logging import Logger, getLogger
from os import path
from typing import Protocol, TypedDict

from discord import File
from PIL import Image, ImageDraw, ImageFilter, ImageFont, UnidentifiedImageError

if path.exists("static/fonts/Arial.ttf"):
    font = ImageFont.truetype("static/fonts/Arial.ttf", 20)
else:
    font = ImageFont.load_default()


__all__: tuple[str, ...] = ("PresenceChart", "PresenceType")


logger: Logger = getLogger("presence-chart")


class PresenceType(TypedDict):
    """PresenceType is a type hint for the presence data.

    Parameters
    ----------
    avatar : `bytes`
        The avatar of the user.
    labels : `list[str]`
        The labels of the pie chart.
    values : `list[int]`
        The values of the pie chart.
    colors : `list[str]`
        The colors of the pie chart.
    """

    avatar: bytes
    labels: list[str]
    values: list[int]
    colors: list[str]


class PresenceChartProtocol(Protocol):
    """PresenceChartProtocol is a protocol for the presence chart."""

    id: str

    def create(self) -> File:
        """Creates the presence chart."""
        ...

    def save(self) -> None:
        """Saves the presence chart."""
        ...


class PresenceChart(PresenceChartProtocol):
    """PresenceChart is a class that generates a presence chart.

    Parameters
    ----------
    presence : `PresenceType`
        The presence data.

    Attributes
    ----------
    id : `str`
        The ID of the chart.
    avatar : `bytes`
        The avatar of the user.
    data : `list[int]`
        The values of the pie chart.
    labels : `list[str]`
        The labels of the pie chart.
    colors : `list[str]`
        The colors of the pie chart.
    inner_radius : `int`
        The inner radius of the pie chart.
    width : `int`
        The width of the image.
    height : `int`
        The height of the image.
    radius : `int`
        The radius of the pie chart.
    center : `tuple[int, int]`
        The center of the pie chart.
    image : `PIL.Image.Image`
        The image of the chart.
    draw : `PIL.ImageDraw.ImageDraw`
        The draw object of the chart.
    """

    def __init__(
        self,
        presence: PresenceType,
    ) -> None:
        self.id = str(uuid.uuid4())[0:8]
        self.avatar = presence["avatar"]

        self.data = presence["values"]
        self.labels = presence["labels"]
        self.colors = presence["colors"]
        self.inner_radius = 140

        self.width = 700
        self.height = 400
        self.radius = min(self.width, self.height) / 2.2
        self.center = (self.radius + 20, self.height / 2)

        # We are lying but it's correct enough
        self.image: Image.Image
        self.draw: ImageDraw.ImageDraw

    def draw_pie_chart(self) -> None:
        """Draws the pie chart."""
        data = self.data
        total = sum(data) or 1
        start_angle = 0

        for i, d in enumerate(data):
            angle = 360 * d / total
            self.draw.pieslice(
                (  # type: ignore
                    self.center[0] - self.radius,
                    self.center[1] - self.radius,
                    self.center[0] + self.radius,
                    self.center[1] + self.radius,
                ),
                start_angle,
                start_angle + angle,
                fill=self.colors[i],
            )
            start_angle += angle

    def clean_inner_circle(self) -> None:
        """Cleans the inner circle of the pie chart."""
        self.draw.ellipse(
            (
                self.center[0] - self.inner_radius,
                self.center[1] - self.inner_radius,
                self.center[0] + self.inner_radius,
                self.center[1] + self.inner_radius,
            ),
            fill=(255, 255, 255, 0),
        )

    def sharpen(self) -> None:
        """Sharpens the image."""
        self.image = self.image.filter(ImageFilter.SHARPEN)

    def draw_cubes(self) -> None:
        """Draws the cubes."""
        total = sum(self.data) or 1

        for i, (color, label) in enumerate(zip(self.colors, self.labels)):
            self.draw.rectangle(
                (self.width - 200, 50 + i * 50, self.width - 165, 80 + i * 50),
                fill=color,
            )

            self.draw.text(
                (self.width - 155, 55 + i * 50),
                f"{label:<10} {round(self.data[i] / total * 100, 2):>5}%",
                font=font,
                align="right",
            )

        self.draw.text(
            (self.width - 155, 55 + len(self.colors) * 50),
            f"Total: {total}",
            font=font,
            align="right",
        )

        try:
            avatar = Image.open(BytesIO(self.avatar)).resize((100, 100))
        except UnidentifiedImageError:
            logger.warning("Invalid avatar image provided.")
        else:
            self.image.paste(avatar, (self.width - 150, 50 + len(self.colors) * 60))

    def unbrighten_image(self) -> None:
        """Unbrightens the image."""
        for x in range(self.width):
            for y in range(self.height):
                pixel = self.image.getpixel((x, y))
                if pixel[3] != 0:
                    self.image.putpixel(
                        (x, y),
                        (
                            int(pixel[0] * 0.8),
                            int(pixel[1] * 0.8),
                            int(pixel[2] * 0.8),
                            pixel[3],
                        ),
                    )

    def create(self) -> File:
        """Creates the chart.

        Returns
        -------
        `File`
            The chart as a file.
        """
        self.image = Image.new("RGBA", (self.width, self.height), (255, 255, 255, 0))
        self.draw = ImageDraw.Draw(self.image)

        funcs = [
            self.draw_pie_chart,
            self.clean_inner_circle,
            self.draw_cubes,
            self.sharpen,
            self.unbrighten_image,
        ]

        for func in funcs:
            func()

        buffer = BytesIO()
        self.image.save(buffer, format="png")
        buffer.seek(0)

        return File(buffer, filename=f"{self.id}.png")

    def save(self, filename: str) -> None:
        """Saves the chart.

        Parameters
        ----------
        filename : `str`
            The filename to save the chart to.
        """
        self.image.save(filename)

    def __str__(self) -> str:
        return f"<PresenceChart id={self.id}>"

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    sample_data: PresenceType = {
        "avatar": b"avatar",
        "labels": ["idle", "online", "dnd", "offline"],
        "values": [731, 1345, 206, 890],
        "colors": ["#fba31c", "#43b581", "#f04747", "#747f8d"],
    }

    chart = PresenceChart(sample_data)

    chart.create()
    chart.save("presence-chart.png")

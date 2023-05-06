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

import datetime as dt
from asyncio import to_thread
from io import BytesIO
from typing import NamedTuple, TypedDict

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

__all__: tuple[str, ...] = ("PresenceEntry", "PresenceData", "PresenceGraph")


class PresenceEntry(NamedTuple):
    snowflake: int
    status: str
    changed_at: dt.datetime


class PresenceData(TypedDict):
    dates: list[dt.datetime]
    statuses: list[str]


class PresenceGraph:
    def __init__(self, data: PresenceData, avatar: bytes) -> None:
        self._data = data
        self._width = 0.2
        self._mapping = {
            "Online": "#5cb85c",
            "Offline": "#d9534f",
            "Idle": "#f0ad4e",
            "DnD": "#808080",
        }
        self._avatar = avatar

    @property
    def data(self) -> PresenceData:
        return self._data

    @property
    def avatar(self) -> bytes:
        return self._avatar

    def _generate_donut_chart(self) -> BytesIO:
        sizes = [self.data["statuses"].count(status) for status in self._mapping.keys()]
        labels, sorted_sizes = zip(
            *sorted(
                zip(self._mapping.keys(), sizes),
                key=lambda x: list(self._mapping.keys()).index(x[0]),
            )
        )

        _, ax = plt.subplots(facecolor="none")  # type: ignore
        ax.set(aspect="equal")  # type: ignore

        ax.pie(  # type: ignore
            sorted_sizes,
            colors=[self._mapping[label] for label in labels],  # type: ignore
            wedgeprops=dict(width=self._width, edgecolor="none"),
        )

        buf = BytesIO()
        plt.savefig(buf, format="png", facecolor="none")  # type: ignore
        buf.seek(0)

        return buf

    def _generate_image(self) -> BytesIO:
        buf = self._generate_donut_chart()

        with Image.new("RGBA", (580, 370), (0, 0, 0, 0)) as img:
            # paste it on the left side
            img.paste(Image.open(buf), (-150, -60))
            font = ImageFont.truetype("static/fonts/Lato-Black.ttf", 12)
            draw = ImageDraw.Draw(img)

            for i, (status, color) in enumerate(self._mapping.items()):
                draw.text(  # type: ignore
                    (430, 77.4 + (i * 50)),
                    status
                    + f" - {round(self.data['statuses'].count(status) / len(self.data['statuses']) * 100, 2)}%",
                    font=font,
                    fill="white",
                )
                draw.rectangle(  # type: ignore
                    (400, 75 + (i * 50), 420, 95 + (i * 50)),
                    fill=color,
                    outline="white",
                )

            with Image.open(BytesIO(self.avatar)) as avatar:
                avatar = avatar.resize((240, 240))

                with Image.new("L", avatar.size, 0) as mask:
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0) + avatar.size, fill=255)
                    img.paste(avatar, (56, 61), mask=mask)

            buf = BytesIO()
            img.save(buf, format="png")
            buf.seek(0)
            return buf

    async def buffer(self) -> BytesIO:
        return await to_thread(self._generate_image)


if __name__ == "__main__":
    import asyncio

    import aiohttp
    import numpy as np

    dates = np.arange(  # type: ignore
        np.datetime64("2021-01-01"), np.datetime64("2021-01-08"), dtype="datetime64[h]"
    )
    statuses = np.random.choice(
        ["Online", "Offline", "Idle", "DnD"], size=100, p=[0.6, 0.2, 0.1, 0.1]
    )

    data = PresenceData(
        dates=dates.tolist(),
        statuses=statuses.tolist(),
    )

    async def main() -> None:
        avatar = "https://cdn.discordapp.com/attachments/1094283696946827334/1104439322431717487/a2a0b1b2-24fe-4238-883a-e21a91510a90.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar) as resp:
                avatar = await resp.read()

        graph = PresenceGraph(data, avatar)
        buf = await graph.buffer()

        with open("test.png", "wb") as f:
            f.write(buf.read())

    asyncio.run(main())

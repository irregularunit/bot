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

import datetime as dt
from asyncio import to_thread
from io import BytesIO
from typing import NamedTuple, TypedDict

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from .abc import SavableByteStream

__all__: tuple[str, ...] = ("PresenceEntry", "PresenceHistory", "PresenceGraph")


class PresenceEntry(NamedTuple):
    snowflake: int
    status: str
    changed_at: dt.datetime


class PresenceHistory(TypedDict):
    dates: list[dt.datetime]
    statuses: list[str]


class PresenceGraph(SavableByteStream):
    __slots__: tuple[str, ...] = ("_data", "_width", "_mapping", "_avatar", "font")

    _data: PresenceHistory
    _width: float
    _mapping: dict[str, str]

    def __init__(self, data: PresenceHistory) -> None:
        self._data = data
        self._width = 0.2
        self._mapping = {
            "Online": "#3ba55d",
            "Offline": "#747f8d",
            "Idle": "#faa81a",
            "Do Not Disturb": "#ed4245",
        }

    @property
    def data(self) -> PresenceHistory:
        return self._data

    def _generate_donut_chart(self) -> BytesIO:
        statuses = self.data["statuses"]
        sizes = [statuses.count(status) for status in self._mapping.keys()]

        labels, sorted_sizes = zip(
            *sorted(
                zip(self._mapping.keys(), sizes),
                key=lambda x: list(self._mapping.keys()).index(x[0]),
            )
        )

        _, ax = plt.subplots(
            facecolor="none",
            figsize=(9, 7),
        )

        status_labels = list(self._mapping.keys())
        status_colors = list(self._mapping.values())
        square_y = np.linspace(0.9, 0.1, len(status_labels))
        label_y = square_y + 0.035

        for i in range(len(status_labels)):
            ax.text(  # type: ignore
                1.60,
                label_y[i],
                status_labels[i],
                ha="left",
                va="top",
                color="white",
            )
            ax.scatter(  # type: ignore
                1.45,
                square_y[i],
                s=300,
                c=status_colors[i],
                marker="s",
            )

        ax.pie(  # type: ignore
            sorted_sizes,
            colors=[self._mapping[label] for label in labels],  # type: ignore
            wedgeprops=dict(width=self._width, edgecolor="none"),
            center=(0.25, 0.5),
            startangle=90,
            counterclock=True,
            pctdistance=1.15,
            textprops=dict(color="white"),
            radius=1,
        )

        canvas = BytesIO()
        plt.savefig(canvas, format="png", facecolor="none", transparent=True)
        plt.close()
        canvas.seek(0)

        with Image.open(canvas) as img:
            img = img.crop((170, 100, 900, 600))

            buffer = BytesIO()
            img.save(buffer, format="png")
            buffer.seek(0)

        return buffer

    async def buffer(self) -> BytesIO:
        return await to_thread(self._generate_donut_chart)

    def raw(self) -> BytesIO:
        return self._generate_donut_chart()

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import calendar
import datetime
import io
import zoneinfo

import discord

__all__: tuple[str, ...] = ("CountingCalender",)


RANGES = [
    "today",
    "yesterday",
    "this week",
    "last week",
    "this month",
    "last month",
    "this year",
    "last year",
    "all time",
]


class CountingCalender:
    def __init__(self, user: int):
        self.user: int = user
        self.time_mapping: dict[str, tuple[float, float]] = {}
        self.build_time_mapping()

    def build_time_mapping(self) -> None:
        start_date = discord.utils.utcnow().timestamp()

        for time in RANGES:
            start_date, end_date = self.get_end_date(time)
            self.time_mapping[time] = start_date, end_date

    def get_end_date(self, time: str) -> tuple[float, float]:
        # Our day starts at 8am until 8am the next day.
        # So if its before 8am, we want to start at 8am yesterday.
        now = datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC")).replace(hour=8, minute=0, second=0, microsecond=0)
        if now.hour < 8:
            now -= datetime.timedelta(days=1)

        ranges = {
            "today": (now, now + datetime.timedelta(days=1)),
            "yesterday": (now - datetime.timedelta(days=1), now),
            "this week": (now - datetime.timedelta(days=now.weekday()), now + datetime.timedelta(days=7 - now.weekday())),
            "last week": (now - datetime.timedelta(days=now.weekday() + 7), now - datetime.timedelta(days=now.weekday())),
            "this month": (
                now.replace(day=1),
                now.replace(day=calendar.monthrange(now.year, now.month)[1]) + datetime.timedelta(days=1),
            ),
            "last month": (now.replace(day=1) - datetime.timedelta(days=1), now.replace(day=1)),
            "this year": (now.replace(month=1, day=1), now.replace(month=12, day=31) + datetime.timedelta(days=1)),
            "last year": (
                now.replace(year=now.year - 1, month=1, day=1),
                now.replace(year=now.year - 1, month=12, day=31) + datetime.timedelta(days=1),
            ),
            "all time": (now.replace(year=2018, month=1, day=1), now + datetime.timedelta(days=1)),
        }

        if time not in ranges:
            raise ValueError(f"Invalid time range: {time}")

        start, end = ranges[time]
        return start.timestamp(), end.timestamp()

    def struct_query(self) -> str:
        # Cursed witchcraft ...
        inital_query = io.StringIO()

        for time, (start, end) in self.time_mapping.items():
            if time == "all time":
                inital_query.write(
                    f"SELECT COUNT(*) FROM owo_counting WHERE uid = {self.user} AND created_at <= to_timestamp({end})"
                )
            else:
                inital_query.write(
                    (
                        f"SELECT COUNT(*) FROM owo_counting WHERE uid = {self.user} AND "
                        f"created_at BETWEEN to_timestamp({start}) AND to_timestamp({end})"
                    )
                )
            if time != "all time":
                inital_query.write(" UNION ALL ")

        return inital_query.getvalue()


if __name__ == "__main__":
    cal = CountingCalender(123456789)
    print(cal.struct_query())

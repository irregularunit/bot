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
from datetime import datetime, timedelta, timezone


def get_insert_day() -> datetime:
    now = datetime.now(timezone.utc)

    if now.hour < 8:
        now -= timedelta(days=1)

    return datetime(now.year, now.month, now.day, hour=8, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def get_insert_month() -> datetime:
    return datetime.now(timezone.utc).replace(day=1, hour=8, minute=0, second=0, microsecond=0)


def get_insert_year() -> datetime:
    return datetime.now(timezone.utc).replace(year=1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    PASSED = "\033[92mPASSED\033[0m"
    FAILED = "\033[91mFAILED\033[0m"

    def test_insert_day() -> bool:
        dates = [get_insert_day() for _ in range(10)]  # type: ignore

        tests = [
            all(date.hour == 8 for date in dates),
            all(date.minute == 0 for date in dates),
            all(date.second == 0 for date in dates),
            all(date.microsecond == 0 for date in dates),
        ]

        return all(tests)

    def test_insert_month() -> bool:
        dates = [get_insert_month() for _ in range(10)]

        tests = [
            all(date.day == 1 for date in dates),
            all(date.hour == 8 for date in dates),
            all(date.minute == 0 for date in dates),
            all(date.second == 0 for date in dates),
            all(date.microsecond == 0 for date in dates),
        ]

        return all(tests)

    def test_insert_year() -> bool:
        dates = [get_insert_year() for _ in range(10)]

        tests = [
            all(date.day == 1 for date in dates),
            all(date.month == 1 for date in dates),
            all(date.hour == 8 for date in dates),
            all(date.minute == 0 for date in dates),
            all(date.second == 0 for date in dates),
            all(date.microsecond == 0 for date in dates),
        ]

        return all(tests)

    for i, r in enumerate([test_insert_day, test_insert_month, test_insert_year]):
        print(f"Test {i + 1}:", PASSED if r() else FAILED)

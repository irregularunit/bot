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

from logging import Logger, getLogger
from operator import eq
from time import perf_counter
from traceback import format_exc
from types import TracebackType
from typing import Optional

__all__: tuple[str, ...] = ("Stopwatch",)


class Stopwatch:
    def __init__(self) -> None:
        self.__start_time: float = 0.0
        self.__stop_time: float = 0.0
        self.__logger = getLogger(__name__)

    def start(self) -> None:
        self.start_time = perf_counter()

    def stop(self) -> None:
        self.stop_time = perf_counter()

    def reset(self) -> float:
        elapsed = self.elapsed
        self.start_time = 0.0
        self.stop_time = 0.0
        return elapsed

    @property
    def start_time(self) -> float:
        return self.__start_time

    @start_time.setter
    def start_time(self, value: float) -> None:
        self.__start_time = value

    @property
    def stop_time(self) -> float:
        return self.__stop_time

    @stop_time.setter
    def stop_time(self, value: float) -> None:
        self.__stop_time = value

    @property
    def elapsed(self) -> float:
        if eq(self.start_time, 0.0):
            return 0.0

        elapsed = (
            self.stop_time - self.start_time
            if self.stop_time
            else perf_counter() - self.start_time
        )

        return elapsed

    @property
    def logger(self) -> Logger:
        return self.__logger

    def __enter__(self) -> Stopwatch:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

        if all((exc_type, exc_val, exc_tb)):
            return self.logger.error(format_exc())

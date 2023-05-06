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
from time import perf_counter
from traceback import format_exc
from types import TracebackType
from typing import Optional

__all__: tuple[str, ...] = ("Stopwatch",)


class Stopwatch:
    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.stop_time: float = 0.0

        self._logger = getLogger(__name__)

    def start(self) -> None:
        self.start_time = perf_counter()

    def stop(self) -> None:
        self.stop_time = perf_counter()

    @property
    def elapsed(self) -> float:
        return perf_counter() - self.start_time

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed * 1000

    @property
    def total(self) -> float:
        return self.stop_time - self.start_time

    @property
    def logger(self) -> Logger:
        return self._logger

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

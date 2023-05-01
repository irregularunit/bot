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

import random
import time
from typing import Callable, Generic, Literal, TypeVar, overload

T = TypeVar('T', bool, Literal[True], Literal[False])

__all__: tuple[str, ...] = ('ExponentialBackoff',)


class ExponentialBackoff(Generic[T]):
    def __init__(self, base: int = 1, *, integral: T = False) -> None:
        self._base: int = base

        self._exp: int = 0
        self._max: int = 10
        self._reset_time: int = base * 2**11
        self._last_invocation: float = time.monotonic()

        rand = random.Random()
        rand.seed()

        self._randfunc: Callable[..., int | float] = (
            rand.randrange if integral else rand.uniform
        )

    @overload
    def delay(self: ExponentialBackoff[Literal[False]]) -> float:
        ...

    @overload
    def delay(self: ExponentialBackoff[Literal[True]]) -> int:
        ...

    @overload
    def delay(self: ExponentialBackoff[bool]) -> int | float:
        ...

    def delay(self) -> int | float:
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation

        if interval > self._reset_time:
            self._exp = 0

        self._exp = min(self._exp + 1, self._max)
        return self._randfunc(0, self._base * 2**self._exp)

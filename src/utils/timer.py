"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

__all__: tuple[str, ...] = ("Timer",)


class Timer:
    """Simple timer to track execution time of a function.

    Functions
    ---------
    start()
        Start the timer.
    stop()
        Stop the timer. > returns the time elapsed.
    reset()
        Reset the timer.
    """

    def __init__(
        self,
        *,
        timer: Callable[..., float] = time.perf_counter,
        unit: str = "s",
        precision: int = 3,
        prefix: str = "",
        suffix: str = "",
    ) -> None:
        self._timer: Callable[..., float] = timer
        self._unit: str = unit
        self._precision: int = precision
        self._prefix: str = prefix
        self._suffix: str = suffix

        self._start: float = 0.0
        self._end: float = 0.0

    def __enter__(self) -> Timer:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.stop()

    def start(self) -> None:
        if self._start != 0.0:
            raise RuntimeError("Timer is running. Use .stop() to stop it")

        self._start = self._timer()

    def stop(self) -> float:
        """Stop the timer and return the time elapsed."""
        if self._start == 0.0:
            raise RuntimeError("Timer is not running. Use .start() to start it")

        self._end = self._timer()
        return self.elapsed

    def reset(self) -> None:
        self._start = 0.0
        self._end = 0.0

        self.start()

    @property
    def elapsed(self) -> float:
        if self._end == 0.0:
            return self.stop()

        return self._end - self._start

    def __str__(self) -> str:
        return f"{self._prefix}{self.elapsed:{self._precision}.{self._precision}f}{self._unit}{self._suffix}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.elapsed})"

    def __float__(self) -> float:
        return self.elapsed

    def __int__(self) -> int:
        return int(self.elapsed)


if __name__ == "__main__":
    import asyncio

    async def test() -> None:
        async def sleep() -> None:
            await asyncio.sleep(1)

        with Timer() as t:
            await sleep()

        print(f"Time elapsed: {t}")

    asyncio.run(test())

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import logging
from contextlib import AbstractContextManager
from datetime import timedelta
from inspect import isawaitable
from io import BytesIO
from pathlib import Path
from types import TracebackType
from typing import (
    Any,
    Awaitable,
    Callable,
    Final,
    Iterable,
    Iterator,
    Literal,
    Optional,
    Self,
    Sequence,
    Type,
    TypeGuard,
    TypeVar,
)

import coloredlogs
import magic
from discord.app_commands import Command as AppCommand
from discord.ext.commands import Command as ExtCommand
from PIL import Image, ImageSequence

T = TypeVar("T")
CommandType = ExtCommand | AppCommand


__all__: tuple[str, ...] = (
    "humanize_seconds",
    "format_list",
    "humanize_timedelta",
    "suppress",
    "async_all",
    "count_source_lines",
    "type_of",
    "setup_logging",
    "num_to_emote",
    "emote_to_num",
    "resize_to_limit",
    "for_all_callbacks",
    "no_sentinel",
)


log: logging.Logger = logging.getLogger(__name__)


PERIODS: Final[Sequence[tuple[str, str, int]]] = (
    ("year", "years", 60 * 60 * 24 * 365),
    ("month", "months", 60 * 60 * 24 * 30),
    ("day", "days", 60 * 60 * 24),
    ("hour", "hours", 60 * 60),
    ("minute", "minutes", 60),
    ("second", "seconds", 1),
)


def format_list(to_format: Sequence[str], /, *, comma: str = ",") -> str:
    length = len(to_format)

    if length == 0:
        raise ValueError("Must provide at least one item")

    if length == 2:
        return " and ".join(to_format)
    if length > 2:
        *most, last = to_format
        h = f"{comma} ".join(most)
        return f"{h}{comma} and {last}"
    return next(iter(to_format))


def humanize_seconds(seconds: float) -> str:
    seconds = int(seconds)
    strings = []
    for period_name, plural_period_name, period_seconds in PERIODS:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 0:
                continue
            unit = plural_period_name if period_value > 1 else period_name
            strings.append(f"{period_value} {unit}")

    return format_list(strings, comma="")


def humanize_timedelta(delta: timedelta) -> str:
    return humanize_seconds(delta.total_seconds())


class suppress(AbstractContextManager[None]):
    """
    Don't use this unless you know what you're doing.

    It's super slow just as contextlib.suppress is. And should
    not be used in contexts where user response is expected.

    Its about 3x slower than just using a try except block.

    Note:
    -----
    This should NOT use `return` within the context of `suppress`.
    Instead, use the `Single Return Law Pattern` to return from the context.
    Reasoning behind this is that static linters will not be able to understand
    that the following context is reachable.
    """

    def __init__(
        self, *exceptions: Type[BaseException], log: Optional[str] = None, capture: bool = True, **kwargs: Any
    ) -> None:
        self._exceptions: tuple[Type[BaseException], ...] = exceptions
        self._log: str = log or "An exception was suppressed: %s"
        self._capture: bool = capture
        self._kwargs: dict[str, Any] = kwargs

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> Optional[bool]:
        if captured := exc_type is not None and issubclass(exc_type, self._exceptions):
            if self._capture:
                log.info(self._log % self._kwargs)

        log.debug("Suppressing exception: %s", exc_type)
        return captured


async def async_all(
    gen: Iterable[T | Awaitable[T]],
    *,
    check: Callable[[T | Awaitable[T]], TypeGuard[Awaitable[T]]] = isawaitable,
) -> bool:
    """Returns True if all elements in the iterable are truthy."""
    for elem in gen:
        if check(elem):
            elem = await elem
        if not elem:
            return False
    return True


def count_source_lines() -> int:
    """Counts the number of lines in the source code."""

    def count_lines_recursive(path: Path) -> Iterator[int]:
        if path.is_file():
            if path.suffix in (".py", ".sql", ".yml"):
                with path.open('r', encoding='utf-8') as f:
                    yield sum(1 for _ in f if _.strip())
        elif path.is_dir():
            if path.name.startswith('__') or path.name.startswith('.venv'):
                return
            for child in path.iterdir():
                yield from count_lines_recursive(child)

    # "." is the aware root of the project
    return sum(count_lines_recursive(Path(".")))


def type_of(image: bytes) -> Optional[str]:
    """Returns the raw mime type of an image buffer."""

    def validate_mime(mime: str) -> bool:
        return mime in ("image/png", "image/jpeg", "image/webp", "image/gif")

    mime = magic.from_buffer(image, mime=True)
    if not validate_mime(mime):
        return None

    return mime.split("/")[1]


def setup_logging(level: int | str) -> None:
    """Call this before doing anything else"""
    coloredlogs.install(
        level=level,
        fmt="[%(asctime)s][%(name)s][%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        field_styles={
            "asctime": {"color": "cyan"},
            "hostname": {"color": "magenta"},
            "levelname": {"bold": True, "color": "black"},
            "name": {"color": "blue"},
            "programname": {"color": "cyan"},
            "username": {"color": "yellow"},
        },
        level_styles={
            "debug": {"color": "magenta"},
            "info": {"color": "green"},
            "warning": {"color": "yellow"},
            "error": {"color": "red"},
            "critical": {"color": "red"},
        },
    )


def num_to_emote(num: int) -> str:
    """Converts a number to an emoji. range is 0-9."""
    return chr(48 + num) + chr(65039) + chr(8419)


def emote_to_num(emote: str) -> int:
    """Converts an emoji to a number. range is 0-9."""
    return ord(emote[0]) - 48


def resize_to_limit(image: BytesIO, limit: int = 8_000_000) -> BytesIO:
    current_size: int = image.getbuffer().nbytes

    while current_size > limit:
        with Image.open(image) as canvas:
            image = BytesIO()
            if canvas.format in ("PNG", "JPEG", "JPG", "WEBP"):
                canvas = canvas.resize([i // 2 for i in canvas.size], resample=Image.BICUBIC)  # type: ignore
                canvas.save(image, format=canvas.format)
            elif canvas.format == "GIF":
                durations, frames = [], []
                for frame in ImageSequence.Iterator(canvas):
                    durations.append(frame.info.get("duration", 0))
                    frames.append(frame.resize([i // 2 for i in frame.size], resample=Image.BICUBIC))

                frames[0].save(
                    image,
                    save_all=True,
                    append_images=frames[1:],
                    format="gif",
                    version=canvas.info.get("version", "GIF89a"),
                    duration=durations,
                    loop=0,
                    background=canvas.info.get("background", 0),
                    palette=canvas.getpalette(),
                )

            image.seek(0)
            current_size = image.getbuffer().nbytes

    return image


def for_all_callbacks(decorator: Any) -> Callable[[Type[T]], Type[T]]:
    """Decorates all function command callbacks in a class"""

    def decorate(cls: Type[T]) -> Type[T]:
        for attr in dir(cls):
            method = getattr(cls, attr)
            if isinstance(method, CommandType):
                setattr(cls, attr, decorator(method))
        return cls

    return decorate


class NoSentinel:
    __slots__: tuple[()] = ()
    __eq__: Callable[..., Literal[False]] = lambda self, _: False
    __bool__: Callable[..., Literal[False]] = lambda self: False
    __hash__: Callable[..., Literal[0]] = lambda self: 0
    __repr__: Callable[..., Literal["..."]] = lambda self: '...'


no_sentinel: Any = NoSentinel()

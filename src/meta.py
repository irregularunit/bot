"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import time
from typing import Final, NamedTuple

__all__: Final[list[str]] = ['__version__', '__author__', '__license__']


class VersionInfo(NamedTuple):
    """A class to represent the version of the bot.

    Parameters
    ----------
    major: :class:`int`
        The major version.
    minor: :class:`int`
        The minor version.
    micro: :class:`int`
        The micro version.
    releaselevel: :class:`str`
        The release level.
    serial: :class:`int`
        The serial number.
    """
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int

    def to_string(self) -> str:
        """Converts the version info to a string.

        Returns
        -------
        :class:`str`
            The version info as a string.
        """
        return f'{self.major}.{self.minor}.{self.micro}{self.releaselevel}#{self.serial}'


def generate_serial_number(major: int, minor: int) -> int:
    """Generates a serial number for the version.

    Parameters
    ----------
    major: :class:`int`
        The major version.
    minor: :class:`int`
        The minor version.

    Returns
    -------
    :class:`int`
        The serial number.
    """
    return int(time.time() * 1000) & 0x7FFFFFFF + (major << 28) + (minor << 24)


__major__: Final[int] = 0
__minor__: Final[int] = 0

__version__: Final[str] = VersionInfo(
    __major__,
    __minor__,
    1,
    'alpha',
    generate_serial_number(__major__, __minor__),
).to_string()
__author__: Final[str] = 'lexicalunit#4564'
__license__: Final[str] = 'CC BY-NC-SA 4.0'
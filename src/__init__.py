# -*- coding: utf-8 -*-

from string import ascii_letters, digits
from typing import Final, NamedTuple

__all__: tuple[str, ...] = (
    "__version__",
    "__author__",
    "__license__",
)

BASE62 = digits + ascii_letters


class VersionInfo(NamedTuple):
    """Represents a version of the bot."""

    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: str

    def to_string(self) -> str:
        """Convert the version to a string."""
        return f"{self.major}.{self.minor}.{self.micro}{self.releaselevel}{self.serial}"


def _generate_serial_number(major: int, minor: int) -> str:
    def encode(number: int, alphabet: str) -> str:
        if number == 0:
            return alphabet[0]

        array: list[str] = [alphabet[divmod(number, len(alphabet))[1]]]

        while number := divmod(number, len(alphabet))[0]:
            array.append(alphabet[divmod(number, len(alphabet))[1]])

        return "".join(reversed(array))

    return encode(major, BASE62) + encode(minor, BASE62)


__major__: Final[int] = 0
__minor__: Final[int] = 2
__version__: Final[str] = VersionInfo(
    major=__major__,
    minor=__minor__,
    micro=1,
    releaselevel="rc",
    serial=_generate_serial_number(__major__, __minor__),
).to_string()

__license__: Final[str] = "CC-BY-NC-SA-4.0"
__author__: Final[str] = "lexicalunit#4564"


if __name__ == "__main__":
    print(f"<Serenity Bot v{__version__} by {__author__} ({__license__})>")

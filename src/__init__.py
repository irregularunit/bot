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

from string import ascii_letters, digits
from typing import Final, Literal, NamedTuple

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
    releaselevel: Literal["a", "b", "rc", "zd", "zr", "f"]
    serial: str

    def to_string(self) -> str:
        """Convert the version to a string."""
        return f"{self.major}.{self.minor}.{self.micro}{self.releaselevel}{self.serial}"


def _generate_serial_number(major: int, minor: int) -> str:
    def b62_encode(number: int, alphabet: str) -> str:
        if number == 0:
            return alphabet[0]

        base = len(alphabet)
        digits: list[str] = []

        while number:
            number, remainder = divmod(number, base)
            digits.append(alphabet[remainder])

        return "".join(reversed(digits))

    return b62_encode(major * 100 + minor, BASE62)


__major__: Final[int] = 0
__minor__: Final[int] = 0
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

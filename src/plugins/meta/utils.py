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

from logging import getLogger
from pathlib import Path
from typing import Final, Tuple

__all__: Tuple[str, ...] = (
    "BRANCH",
    "GITHUB_URL",
    "LICENSE",
    "count_source_lines",
)

BRANCH: Final[str] = "master"
GITHUB_URL: Final[str] = "https://github.com/irregularunit/bot"
LICENSE: Final[str] = "https://creativecommons.org/licenses/by-nc-sa/4.0/"

_logger = getLogger(__name__)


def count_source_lines() -> int:
    def count_lines(path: Path) -> int:
        if path.is_file():
            ignored = (".png",)

            if path.suffix in ignored:
                return 0

            with path.open("r", encoding="utf-8") as file:
                try:
                    return len(file.readlines())
                except UnicodeDecodeError:
                    _logger.warning(f"Failed to read {path} as UTF-8.")
                    return 0

        elif path.is_dir():
            if path.name.startswith("__"):
                return 0

            return sum(count_lines(child) for child in path.iterdir())

        return 0

    return count_lines(Path("src"))

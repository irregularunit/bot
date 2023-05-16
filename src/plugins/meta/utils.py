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

import textwrap
from logging import getLogger
from os import environ
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any, Dict, Final, List, NamedTuple, Tuple

__all__: Tuple[str, ...] = (
    "BRANCH",
    "GITHUB_URL",
    "LICENSE",
    "count_source_lines",
    "get_git_history",
    "RESTART_ID",
)

RESTART_ID: Final[int] = 42
BRANCH: Final[str] = "main"
GITHUB_URL: Final[str] = "https://github.com/irregularunit/bot"
LICENCE_SHORT: Final[str] = "CC-BY-NC-SA-4.0"
LICENSE: Final[str] = "https://creativecommons.org/licenses/by-nc-sa/4.0/"

_logger = getLogger(__name__)


class SourceInformation(NamedTuple):
    url: str
    lines: int
    filename: str
    module: str
    notes: str = f"**Licence**: [{LICENCE_SHORT}]({LICENSE})"


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


def get_git_history():
    def ext_command(command: List[str]) -> bytes:
        env: Dict[str, Any] = {}

        for k in ["SYSTEMROOT", "PATH"]:
            v = environ.get(k)

            if v is not None:
                env[k] = v

        # W32 - LANGUAGE
        env["LANGUAGE"] = "C"

        env["LANG"] = "C"
        env["LC_ALL"] = "C"

        out = Popen(command, stdout=PIPE, env=env).communicate()[0]

        return out

    try:
        first = ext_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        branch = first.strip().decode("ascii")

        second = ext_command(["git", "log", "--oneline", "-5"])
        history = second.strip().decode("ascii")

        return "Branch:\n" + textwrap.indent(branch, "  ") + "\nCommit history:\n" + textwrap.indent(history, "  ")
    except OSError:
        return "Failed to get git history."

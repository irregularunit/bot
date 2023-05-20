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

import inspect
import re
import textwrap
from logging import getLogger
from os import environ
from pathlib import Path
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Any, Dict, Final, List, NamedTuple, Optional, Tuple

from discord.ext import commands

if TYPE_CHECKING:
    from src.models.serenity import Serenity


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


class SourceCode:
    __slots__ = ("object", "bot", "_git")

    object: Optional[str]
    bot: Serenity
    _git: str

    def __init__(self, serenity: Serenity, object: Optional[str]) -> None:
        self.object = object
        self.bot = serenity
        self._git = GITHUB_URL

    def _get_command_options(self) -> List[str]:
        return list(
            filter(
                None,
                map(lambda cmd: cmd.qualified_name, self.bot.walk_commands()),
            )
        )

    def _generate_source_link(self, command: str, path: str) -> str:
        return f"[`{command}`]({GITHUB_URL}/blob/{BRANCH}/{path})"

    def _generate_source_info(
        self, target: commands.Command[Any, ..., Any]
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        lines = inspect.getsourcelines(target.callback)[1]
        filename = inspect.getsourcefile(target.callback)

        module = inspect.getmodule(target.callback)
        if module is not None:
            module = module.__name__

        return filename, lines, module

    def source(self) -> str:
        if not self.object:
            return self._git

        commands = self._get_command_options()

        if self.object == "help":
            return self._git
        else:
            target_command = self.bot.get_command(self.object)

        if target_command is None:
            return f"Command `{self.object}` not found.\n\nAvailable commands:\n{', '.join(commands)}"

        filename, lines, module = self._generate_source_info(target_command)
        module = module or "Unknown"

        if not filename:
            return f"Unable to locate source code for `{self.object}`."

        filename = filename.split("bot/")[1].replace("\\", "/")
        link = self._generate_source_link(self.object, filename)

        fmt = f"""
            <{link}>
            ```prolog
            === Source code for "{self.object}" ===

            {module} ({filename})
            Lines: {lines}
            ```
            """

        return re.sub(r"(?m)^ {12}", "", fmt)

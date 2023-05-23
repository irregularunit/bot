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

from typing import AnyStr, Optional

__all__: tuple[str, ...] = ("Codeblock",)


class Codeblock:
    """A class to represent a discord codeblock.

    Attributes
    ----------
    content: `str`
        The content of the codeblock.
    language: `Optional[str]`
        The language of the codeblock.
    """

    content: str
    language: Optional[str]
    inline: bool = False

    def __init__(self, content: AnyStr, *, language: Optional[str] = None, inline: bool = False) -> None:
        if isinstance(content, str):
            self.content = content
        else:
            try:
                self.content = content.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Content must be a string or bytes-like object.")

        self.language = language
        self.inline = inline

    def __str__(self) -> str:
        return f"{self.language or ''}\n{self.content}"

    def to_string(self) -> str:
        if self.inline:
            return f"`{self.content}`"
        else:
            return f"```{self.language or ''}\n{self.content}\n```"

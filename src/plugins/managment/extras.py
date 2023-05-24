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

from src.shared import CommandExtras, CommandOption, DefaultArg

prefix_extra = CommandExtras(
    description="Get or set the prefix for the bot.",
    options=(CommandOption("prefix", "The prefix to set the bot to listen for."),),
    example=f"{DefaultArg} s? | <subcommand>",
)


prefix_list_extra = CommandExtras(
    description="Get the list of prefixes the bot listens for.",
    options=(),
    example=DefaultArg,
)


prefix_remove_extra = CommandExtras(
    description="Remove a prefix the bot listens for.",
    options=(CommandOption("prefix", "The prefix to remove."),),
    example=f"{DefaultArg} s?",
)

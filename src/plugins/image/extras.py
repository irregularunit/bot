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

avatar_history_extra = CommandExtras(
    description="Generate a collage of a user's avatar history.",
    options=(CommandOption("user", "The user to generate the avatar history for."),),
    example=DefaultArg + " @lexicalunit"
)

presence_graph_extra = CommandExtras(
    description="Generate a graph of a user's presence history.",
    options=(CommandOption("user", "The user to generate the presence history for."),),
    example=DefaultArg + " @lexicalunit"
)

palette_extra = CommandExtras(
    description="Generate a color pallete from an user's avatar.",
    options=(CommandOption("user", "The user to generate the color pallete for."),),
    example=DefaultArg + " @lexicalunit"
)

ascii_extra = CommandExtras(
    description="Generate an ASCII art image from an user's avatar.",
    options=(CommandOption("user", "The user to generate the ASCII art for."),),
    example=DefaultArg + " @lexicalunit",
)

pixelate_extra = CommandExtras(
    description="Generate a pixelated image from an user's avatar.",
    options=(CommandOption("user", "The user to generate the pixelated image for."),),
    example=DefaultArg + " @lexicalunit",
)

pride_extra = CommandExtras(
    description="Generate a pride flag image from an user's avatar.",
    options=(
        CommandOption("flag", "The flag to use."),
        CommandOption("user", "The user to generate the pride image for."),
    ),
    example=DefaultArg + " nonbinary @lexicalunit",
)

triggered_extra = CommandExtras(
    description="Generate a triggered image from an user's avatar.",
    options=(CommandOption("user", "The user to generate the triggered image for."),),
    example=DefaultArg + " @lexicalunit",
)

color_extra = CommandExtras(
    description="Generate a color image from color input.",
    options=(CommandOption("color", "The color to generate the image for."),),
    example=DefaultArg + " #ff0000",
)

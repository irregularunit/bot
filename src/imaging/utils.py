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

from difflib import get_close_matches
from typing import Optional

__all__: tuple[str, ...] = ("rgb_to_hex", "pride_options", "get_pride_type")


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Converts an RGB tuple to a hex string.

    Parameters
    ----------
    rgb : `tuple` [`int`, `int`, `int`]
        The RGB tuple to convert.

    Returns
    -------
    `str`
        The hex string representation of the RGB tuple.
    """
    return ('#%02x%02x%02x' % rgb).upper()


pride_options = {
    'agender',
    'bigender',
    'transgender',
    'pangender',
    'trigender',
    'androgyne',
    'asexual',
    'omnisexual',
    'demisexual',
    'intersex',
    'lesbian',
    'genderfluid',
    'polyamory',
    'aromantic',
    'pansexual',
    'demigirl',
    'bisexual',
    'demiboy',
    'genderqueer',
    'nonbinary',
    'gay',
    'polysexual',
}


def get_pride_type(option: str) -> Optional[str]:
    """Gets the closest pride option to the given option.

    Parameters
    ----------
    option : `str`
        The option to get the closest pride option to.

    Returns
    -------
    `str`
        The closest pride option.
    """
    matches = get_close_matches(option, pride_options, 1, 0.5)
    return matches[0] if matches else None

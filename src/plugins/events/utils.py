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

from datetime import datetime
from io import BytesIO
from typing import NamedTuple, Optional, Tuple

import discord
from magic import from_buffer

from src.imaging import AvatarPointer

__all__: Tuple[str, ...] = (
    "PRESENCE_STATUS",
    "PresenceEntitiy",
    "AssetEntity",
    "get_image_mime_type",
)

PRESENCE_STATUS = {
    discord.Status.online: "Online",
    discord.Status.idle: "Idle",
    discord.Status.dnd: "Do Not Disturb",
    discord.Status.offline: "Offline",
}


class PresenceEntitiy(NamedTuple):
    snowflake: int
    status: str
    changed_at: datetime


class AssetEntity(NamedTuple):
    snowflake: int
    image_data: bytes
    mime_type: str

    def to_pointer(self) -> AvatarPointer:
        return AvatarPointer(self.snowflake, self.mime_type, file=BytesIO(self.image_data))


def get_image_mime_type(data: bytes) -> Optional[str]:
    mime = from_buffer(data, mime=True)

    if mime in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        return mime

    return None

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from .collage import CollageAvatarButton
from .names import NameHistoryButton

__all__: tuple[str, ...] = ("CollageAvatarButton", "NameHistoryButton")

"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable

from discord.ext.commands import CommandError

__all__: tuple[str, ...] = (
    "ExceptionLevel",
    "UserFeedbackExceptionFactory",
    "UserFeedbackException",
)


class ExceptionLevel(Enum):
    """Enum for the level of an exception.
    
    Attributes
    ----------
    ERROR: `int`
        The error level.
    WARNING: `int`
        The warning level.
    INFO: `int`
        The info level.
    """
    ERROR = 1
    WARNING = 2
    INFO = 3


class UserFeedbackException(CommandError):
    """A class to represent an exception that will be displayed to the user.

    Parameters
    ----------
    message: :class:`str`
        The message to be displayed to the user.
    emoji_strategy: :class:`UserFeedbackEmojiStrategy`
        The emoji strategy to be used.
    formatters: :class:`tuple[Callable[[str], str], ...]`
        Can be a function or a list of lambda functions that will be applied to the message.

    Attributes
    ----------
    message: :class:`str`
        The message to be displayed to the user.
    emoji_strategy: :class:`UserFeedbackEmojiStrategy`
        The emoji strategy to be used.
    formatters: :class:`tuple[Callable[[str], str], ...]`
        Can be a function or a list of lambda functions that will be applied to the message.
    """

    def __init__(
        self,
        message: str,
        emoji_strategy: UserFeedbackEmojiStrategy,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> None:
        self.message: str = message
        self.emoji_strategy: UserFeedbackEmojiStrategy = emoji_strategy
        self.formatters: tuple[Callable[[str], str], ...] = formatters
        super().__init__(message)

    def to_string(self) -> str:
        """Returns a string representation of the exception."""
        formatted_message: str = self.message
        for formatter in self.formatters:
            formatted_message = formatter(formatted_message)
        return f"**{self.emoji_strategy.get_emoji()} |** {formatted_message}"


class UserFeedbackEmojiStrategy(ABC):
    """An abstract class to represent a strategy for getting an emoji."""
    @abstractmethod
    def get_emoji(self) -> str:
        """Returns the emoji."""
        pass


class DefaultUserFeedbackEmoji(UserFeedbackEmojiStrategy):
    """A class to represent the default emoji strategy."""
    def get_emoji(self) -> str:
        return "🔍"


class ErrorUserFeedbackEmoji(UserFeedbackEmojiStrategy):
    """A class to represent the error emoji strategy."""
    def get_emoji(self) -> str:
        return "❌"


class WarningUserFeedbackEmoji(UserFeedbackEmojiStrategy):
    """A class to represent the warning emoji strategy."""
    def get_emoji(self) -> str:
        return "⚠️"


class InfoUserFeedbackEmoji(UserFeedbackEmojiStrategy):
    """A class to represent the info emoji strategy."""
    def get_emoji(self) -> str:
        return "📨"


class UserFeedbackExceptionFactory:
    """A class to represent a factory for creating user feedback exceptions.
    
    Attributes
    ----------
    EMOJI_STRATEGIES: `dict[ExceptionLevel, UserFeedbackEmojiStrategy]`
        A dictionary of emoji strategies.
    """
    EMOJI_STRATEGIES = {
        ExceptionLevel.ERROR: ErrorUserFeedbackEmoji(),
        ExceptionLevel.WARNING: WarningUserFeedbackEmoji(),
        ExceptionLevel.INFO: InfoUserFeedbackEmoji(),
    }

    @staticmethod
    def create(
        message: str,
        level: ExceptionLevel = ExceptionLevel.ERROR,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> UserFeedbackException:
        """Creates a user feedback exception.

        Parameters
        ----------
        message: :class:`str`
            The message to be displayed to the user.
        level: :class:`ExceptionLevel`
            The level of the exception.
        formatters: :class:`tuple[Callable[[str], str], ...]`
            Can be a function or a list of lambda functions that will be applied to the message.

        Returns
        -------
        :class:`UserFeedbackException`
            The user feedback exception.
        """
        return UserFeedbackException(
            message,
            # Probably not the best idea to default to DefaultUserFeedbackEmoji
            # but I guess it's fine for now. I'll probably change this later.
            UserFeedbackExceptionFactory.EMOJI_STRATEGIES.get(level, DefaultUserFeedbackEmoji()),
            formatters,
        )

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

from abc import ABC, abstractmethod
from enum import Enum
from io import StringIO
from typing import Callable, ClassVar

from discord.ext import commands

__all__: tuple[str, ...] = (
    "ExecptionLevel",
    "ExceptionFactory",
    "UserFeedbackException",
)


# fmt: off
class ExecptionLevel(Enum):
    """An enum for exception levels.
    
    This is used to notify the user of the severity of the exception.
    
    Notes
    -----
    - Info: The exception is not severe and can be ignored.
    - Warning: The exception is not severe, but should be noted.
    - Error: The exception is severe and should be noted.
    - Critical: The exception is severe and should be noted immediately.
    
    +----------------+-------------------+
    | Level          | Emoji             |
    +================+===================+
    | INFO           | ℹ️                |
    +----------------+-------------------+
    | WARNING        | ⚠️                 |
    +----------------+-------------------+
    | ERROR          | ❌                |
    +----------------+-------------------+
    | CRITICAL       | 🚨                |
    +----------------+-------------------+
    """
    INFO        = 0
    WARNING     = 1
    ERROR       = 2
    CRITICAL    = 3
# fmt: on


class UserFeedbackException(commands.CommandError):
    """An exception that notifies the user of the severity of the exception."""

    def __init__(
        self,
        message: str,
        strategy: UserFeedbackStrategy,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> None:
        self.message = message
        self.strategy = strategy
        self.formatters = formatters

    def to_string(self) -> str:
        buffer = StringIO()
        if self.formatters:
            for formatter in self.formatters:
                buffer.write(formatter(self.message))
        else:
            buffer.write(self.message)

        return f"{self.strategy.get_emoji()} | {buffer.getvalue()}"


class UserFeedbackStrategy(ABC):
    @abstractmethod
    def get_emoji(self) -> str:
        ...


class InfoStrategy(UserFeedbackStrategy):
    def get_emoji(self) -> str:
        return "ℹ️"


class WarningStrategy(UserFeedbackStrategy):
    def get_emoji(self) -> str:
        return "⚠️"


class ErrorStrategy(UserFeedbackStrategy):
    def get_emoji(self) -> str:
        return "❌"


class CriticalStrategy(UserFeedbackStrategy):
    def get_emoji(self) -> str:
        return "🚨"


class ExceptionFactory:
    """Exception factory for creating exceptions."""

    strategies: ClassVar[dict[ExecptionLevel, UserFeedbackStrategy]] = {
        ExecptionLevel.INFO: InfoStrategy(),
        ExecptionLevel.WARNING: WarningStrategy(),
        ExecptionLevel.ERROR: ErrorStrategy(),
        ExecptionLevel.CRITICAL: CriticalStrategy(),
    }

    @staticmethod
    def create_exception(
        level: ExecptionLevel,
        message: str,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> UserFeedbackException:
        """A factory for creating exceptions.

        This factory is used to create exceptions that notify the user of the
        severity of the exception.

        Parameters
        ----------
        level: `ExecptionLevel`
            The level of the exception.
        message: `str`
            The message of the exception.
        formatters: `tuple[Callable[[str], str], ...]`
            The formatters to apply to the message.

        Returns
        -------
        `UserFeedbackException`
            The exception that was created.
        """
        return UserFeedbackException(
            message, ExceptionFactory.strategies[level], formatters
        )

    @staticmethod
    def create_info_exception(
        message: str,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> UserFeedbackException:
        return ExceptionFactory.create_exception(
            ExecptionLevel.INFO, message, formatters
        )

    @staticmethod
    def create_warning_exception(
        message: str,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> UserFeedbackException:
        return ExceptionFactory.create_exception(
            ExecptionLevel.WARNING, message, formatters
        )

    @staticmethod
    def create_error_exception(
        message: str,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> UserFeedbackException:
        return ExceptionFactory.create_exception(
            ExecptionLevel.ERROR, message, formatters
        )

    @staticmethod
    def create_critical_exception(
        message: str,
        formatters: tuple[Callable[[str], str], ...] = (),
    ) -> UserFeedbackException:
        return ExceptionFactory.create_exception(
            ExecptionLevel.CRITICAL, message, formatters
        )

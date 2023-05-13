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

from logging import getLogger
from typing import Any, Callable, Optional, Tuple, Type, TypeAlias, TypeVar, Union

from discord.ext import commands

from src.models.discord import SerenityContext
from src.shared import UserFeedbackException

from .utils import INTERNAL_EXCEPTION, converter_name, get_raisable_context

__all__: Tuple[str, ...] = (
    "register_handler",
    "get_handler",
    "get_message",
)


logger = getLogger(__name__)
T_co = TypeVar("T_co", covariant=True)
T_return: TypeAlias = Union[Optional[str], Union[str, None]]
T_handler: TypeAlias = Callable[[SerenityContext, Any], T_return]

EXCEPTION_HANDLERS: dict[Type[commands.CommandError], T_handler] = {}


def register_handler(
    exc_type: Type[commands.CommandError],
) -> Callable[[T_handler], T_handler]:
    def decorator(func: T_handler) -> T_handler:
        EXCEPTION_HANDLERS[exc_type] = func

        return func

    return decorator


def get_handler(
    exc_type: Type[commands.CommandError],
) -> Optional[T_handler]:
    chain = type(exc_type).__mro__

    try:
        return next(filter(None, map(EXCEPTION_HANDLERS.get, chain)))
    except StopIteration:
        return None


def get_message(
    ctx: SerenityContext,
    exc: commands.CommandError,
) -> Union[str, None]:
    handler = get_handler(type(exc))

    if handler is not None:
        return handler(ctx, exc)

    return str(exc)


@register_handler(commands.CommandNotFound)
@register_handler(commands.CheckFailure)
@register_handler(commands.DisabledCommand)
def null_handler(
    ctx: SerenityContext,
    exc: Union[commands.CommandNotFound, commands.CheckFailure, commands.DisabledCommand],
) -> T_return:
    return None


@register_handler(UserFeedbackException)
def user_feedback_handler(
    ctx: SerenityContext,
    exc: UserFeedbackException,
) -> T_return:
    return exc.to_string()


@register_handler(commands.CommandError)
def command_error_handler(
    ctx: SerenityContext,
    exc: commands.CommandError,
) -> T_return:
    return INTERNAL_EXCEPTION


@register_handler(commands.ConversionError)
def conversion_error_handler(
    ctx: SerenityContext,
    exc: commands.ConversionError,
) -> T_return:
    if ctx.command is None:
        return INTERNAL_EXCEPTION

    converter = converter_name(exc.converter)

    logger.exception(
        "Unhandled conversion error in command %s: %s",
        ctx.command.qualified_name,
        converter,
        exc_info=exc,
    )

    return INTERNAL_EXCEPTION


@register_handler(commands.MissingRequiredArgument)
def missing_argument_handler(
    ctx: SerenityContext,
    exc: commands.MissingRequiredArgument,
) -> T_return:
    param, signature = get_raisable_context(ctx)
    return f"The `{param.name}` parameter is required. {signature}"


@register_handler(commands.TooManyArguments)
def too_many_arguments_handler(
    ctx: SerenityContext,
    exc: commands.TooManyArguments,
) -> T_return:
    if ctx.command is None:
        return INTERNAL_EXCEPTION

    return (
        f"Too many arguments were passed.\n"
        f"Please check `{ctx.prefix}help {ctx.command.qualified_name}` for more information."
    )


@register_handler(commands.BadArgument)
def bad_argument_handler(
    ctx: SerenityContext,
    exc: commands.BadArgument,
) -> T_return:
    error_message = str(exc)
    param, signature = get_raisable_context(ctx)

    return f"Invalid value for `{param.name}`: {error_message}{signature}"


@register_handler(commands.MissingPermissions)
@register_handler(commands.BotMissingPermissions)
def missing_permissions_handler(
    ctx: SerenityContext,
    exc: Union[commands.MissingPermissions, commands.BotMissingPermissions],
) -> T_return:
    perms = exc.missing_permissions

    if len(perms) <= 2:
        formatted = "` and `".join(perms)
    else:
        formatted = "`, `".join(perms[:-1]) + f"`, and `{perms[-1]}`"

    s = "s" if len(perms) > 1 else ""
    missing = formatted.replace("_", " ").replace("guild", "server")

    me_or_you = "I\'m" if isinstance(exc, commands.BotMissingPermissions) else "You\'re"

    return f"{me_or_you} missing the `{missing}` permission{s} required to run this command."


@register_handler(commands.UnexpectedQuoteError)
@register_handler(commands.InvalidEndOfQuotedStringError)
@register_handler(commands.ExpectedClosingQuoteError)
def quote_error_handler(
    ctx: SerenityContext,
    exc: Union[
        commands.UnexpectedQuoteError,
        commands.InvalidEndOfQuotedStringError,
        commands.ExpectedClosingQuoteError,
    ],
) -> T_return:
    error_message = str(exc)
    stop = "" if error_message.endswith(".") else "."

    return f"{error_message}{stop}".replace("\'", "`")


@register_handler(commands.NoPrivateMessage)
def no_private_message_handler(
    ctx: SerenityContext,
    exc: commands.NoPrivateMessage,
) -> T_return:
    return "Sorry, I don't do dm's."

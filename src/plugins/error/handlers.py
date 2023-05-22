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
from typing import Awaitable, Callable, Dict, Optional, ParamSpec, Tuple, Type, TypeVar, Union

from discord import HTTPException
from discord.ext import commands

from src.models.discord import SerenityContext
from src.shared import UserFeedbackException
from src.shared.exceptions import ExceptionFactory

from .utils import INTERNAL_EXCEPTION, converter_name, get_raisable_context

__all__: Tuple[str, ...] = (
    "register_handler",
    "get_handler",
    "get_message",
)

logger = getLogger(__name__)

T = TypeVar('T')
P = ParamSpec('P')
T_error = TypeVar('T_error', bound=commands.CommandError)
MaybeCoro = Union[T, Awaitable[T]]
MaybeCoroFunc = Callable[P, 'MaybeCoro[T]']

EXCEPTION_HANDLERS: Dict[
    Type[commands.CommandError], Callable[[SerenityContext, commands.CommandError], Union[str, None]]
] = {}


def register_handler(
    *exc_type: Type[T_error],
) -> Callable[[MaybeCoroFunc[P, T]], MaybeCoroFunc[P, T]]:
    """
    Decorator that registers a function as a handler for one or more specified exceptions.
    The handler function will be called when an exception of the specified type(s) is raised.

    Parameters
    ----------
    exc_type : `Union[Type[T_error], Tuple[Type[T_error], ...]]`
        One or more exception types to register the decorated function as a handler for.

    Returns
    -------
    `Callable[[MaybeCoroFunc[P, T]], MaybeCoroFunc[P, T]]`
        The decorator function that can be used to decorate the handler function.

    Raises
    ------
    `TypeError`
        If the `exc_type` parameter is not a type or a tuple of types.

    Example
    -------
    The following example shows how to use the `register_handler` decorator to register a handler
    function for three different types of exceptions:

    >>> @register_handler(
    ...     commands.CommandNotFound,
    ...     commands.CheckFailure,
    ...     commands.DisabledCommand
    ... )
    ... def null_handler(
    ...     ctx: SerenityContext,
    ...     exc: Union[
    ...         commands.CommandNotFound,
    ...         commands.CheckFailure,
    ...         commands.DisabledCommand
    ...     ],
    ... ) -> None:
    ...     return None

    In this example, the `null_handler` function will be called if any of the specified exceptions
    are raised.

    The following example shows how to use the `register_handler` decorator to register a handler
    function for a custom exception type:

    >>> @register_handler(UserFeedbackException)
    ... def user_feedback_handler(
    ...     ctx: SerenityContext,
    ...     exc: UserFeedbackException,
    ... ) -> str:
    ...     return exc.to_string()

    In this example, the `user_feedback_handler` function will be called if a `UserFeedbackException`
    is raised.
    """

    def decorator(func: ...) -> ...:
        """
        Inner function that decorates the handler function and registers it as a handler
        for the specified exception type(s).
        """
        for exc in exc_type:
            EXCEPTION_HANDLERS[exc] = func

        return func

    return decorator


def get_handler(
    exc_type: commands.CommandError,
) -> Optional[Callable[[SerenityContext, commands.CommandError], Union[str, None]]]:
    """
    Returns the exception handler function for the specified exception type, if one exists.

    Parameters
    ----------
    exc_type : `commands.CommandError`
        The type of exception to get the handler function for.

    Returns
    -------
    `Optional[Callable[[SerenityContext, commands.CommandError], Union[str, None]]]`
        The exception handler function for the specified exception type, if one exists.
        Otherwise, `None`.

    Example
    -------
    The following example shows how to use the `get_handler` function to get the handler
    function for a specified exception type:

    >>> handler_func = get_handler(commands.CommandNotFound)

    In this example, the `handler_func` variable will contain the exception handler function
    for the `commands.CommandNotFound` exception type, if one exists.
    """
    chain = type(exc_type).__mro__

    try:
        return next(filter(None, map(EXCEPTION_HANDLERS.get, chain)))
    except StopIteration:
        return None


def get_message(
    ctx: SerenityContext,
    exc: commands.CommandError,
) -> Union[str, None]:
    """
    Returns the error message for the specified exception, using the appropriate exception
    handler function if one exists.

    Parameters
    ----------
    ctx : `SerenityContext`
        The context of the command that raised the exception.
    exc : `commands.CommandError`
        The exception to get the error message for.

    Returns
    -------
    `Union[str, None]`
        The error message for the specified exception, if one exists.
        Otherwise, `None`.

    Example
    -------
    The following example shows how to use the `get_message` function to get the error
    message for a specified exception:

    >>> message = get_message(ctx, commands.CommandNotFound())

    In this example, the `message` variable will contain the error message for a
    `commands.CommandNotFound` exception, if one exists.
    """
    handler = get_handler(exc)

    if handler is not None:
        return handler(ctx, exc)

    return None


@register_handler(commands.CommandNotFound, commands.CheckFailure, commands.DisabledCommand)
def null_handler(
    ctx: SerenityContext,
    exc: Union[commands.CommandNotFound, commands.CheckFailure, commands.DisabledCommand],
) -> None:
    return None


@register_handler(UserFeedbackException)
def user_feedback_handler(
    ctx: SerenityContext,
    exc: UserFeedbackException,
) -> str:
    return exc.to_string()


@register_handler(commands.CommandError)
def command_error_handler(
    ctx: SerenityContext,
    exc: commands.CommandError,
) -> Optional[str]:
    if ctx.command is None:
        return None

    logger.exception(
        "Unhandled error in command %s for user %s (%d):",
        ctx.command.qualified_name,
        ctx.author,
        ctx.author.id,
        exc_info=exc,
    )

    return None


@register_handler(commands.CommandOnCooldown)
async def cooldown_handler(
    ctx: SerenityContext,
    exc: commands.CommandOnCooldown,
) -> None:
    bot = ctx.bot

    if await bot.redis.exists(f"{ctx.author.id}:RateLimit:Command"):
        return None

    await bot.redis.setex(
        name=f"{ctx.author.id}:RateLimit:Command",
        time=int(exc.retry_after) + 1,
        value="command cooldown",
    )

    try:
        return await ctx.message.add_reaction("\N{SNAIL}")
    except HTTPException:
        return None


@register_handler(commands.ConversionError)
def conversion_error_handler(
    ctx: SerenityContext,
    exc: commands.ConversionError,
) -> str:
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
) -> str:
    param, signature = get_raisable_context(ctx)
    return f"The `{param.name}` parameter is required. {signature}"


@register_handler(commands.TooManyArguments)
def too_many_arguments_handler(
    ctx: SerenityContext,
    exc: commands.TooManyArguments,
) -> str:
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
) -> str:
    error_message = str(exc)
    param, signature = get_raisable_context(ctx)

    return f"Invalid value for `{param.name}`: {error_message}{signature}"


@register_handler(commands.MissingPermissions, commands.BotMissingPermissions)
def missing_permissions_handler(
    ctx: SerenityContext,
    exc: Union[commands.MissingPermissions, commands.BotMissingPermissions],
) -> str:
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
) -> str:
    error_message = str(exc)
    stop = "" if error_message.endswith(".") else "."

    return f"{error_message}{stop}".replace("\'", "`")


@register_handler(commands.NoPrivateMessage)
def no_private_message_handler(
    ctx: SerenityContext,
    exc: commands.NoPrivateMessage,
) -> str:
    return "Sorry, I don't do dm's."


@register_handler(commands.BadUnionArgument)
def bad_union_argument_handler(
    ctx: SerenityContext,
    exc: commands.BadUnionArgument,
) -> str:
    return ExceptionFactory.create_critical_exception(str(exc)).to_string()

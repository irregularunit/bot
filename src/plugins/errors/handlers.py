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

import re
from logging import getLogger
from typing import TYPE_CHECKING, Any, Callable, Optional, Type, Union

from discord.ext import commands

from src.shared import UserFeedbackException

if TYPE_CHECKING:
    from src.models.discord import SerenityContext

__all__: tuple[str, ...] = (
    "INTERNAL_ERROR",
    "ERROR_HANDLERS",
    "get_handler",
    "register_handler",
    "get_message",
)


ERROR_HANDLERS: dict[Type[BaseException], Callable[..., Any]] = {}
INTERNAL_ERROR = "Something went wrong internally. Please try again later."

logger = getLogger(__name__)


# I don't know how to type this properly
def coverter_name(converter: Any) -> str:
    try:
        return converter.__name__
    except AttributeError:
        return type(converter).__name__


def get_failed_param(ctx: SerenityContext) -> commands.Parameter:
    """Get which parameter a CheckFailure failed on.

    Some errors only have error text, and no useful attributes giving us this information.

    Parameters
    ----------
    ctx : `SerenityContext`
        The context of the command that errored.

    Returns
    -------
    `commands.Parameter`
        The parameter that failed.

    Raises
    ------
    `commands.CommandError`
        If the context has no command.
    """
    if ctx.command is None:
        raise commands.CommandError(INTERNAL_ERROR)

    params = tuple(ctx.command.params.values())
    handled = (*ctx.args, *ctx.kwargs.values())

    return params[len(handled) - 2]


def get_raisable_context(ctx: SerenityContext) -> tuple[commands.Parameter, str]:
    """Get the failed parameter and a common signature for error messages.

    Parameters
    ----------
    ctx : `SerenityContext`
        The context of the command that errored.

    Returns
    -------
    `commands.Parameter`
        The parameter that failed.
    `str`
        A common signature for error messages.

    Raises
    ------
    `commands.CommandError`
        If the context has no command.
    """
    if ctx.command is None:
        raise commands.CommandError(INTERNAL_ERROR)

    param = get_failed_param(ctx)

    name = ctx.command.qualified_name
    prefix = ctx.clean_prefix

    # Highlight the failed param in bold
    # Result will be [name]`**`<name>`** or similar
    # Adds a zws around the match so results show properly on the Android app
    usage = re.sub(
        fr'(\s*[<\[]{param.name}[.=\w]*[>\]]\s*)',
        '`**`\u200b\\1\u200b`**`',
        ctx.command.signature,
    )
    usage = usage.rstrip('`') if usage.endswith('*`') else f'{usage}`'

    signature = (
        f'\n\nUsage: `{prefix}{name} {usage}\n'
        f'See `{prefix}help {name}` for more information.'
    )

    return param, signature


def register_handler(
    exc_type: Type[BaseException],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a handler for a specific exception type.

    Parameters
    ----------
    exc_type : `Type[BaseException]`
        The exception type to register a handler for.

    Returns
    -------
    `Callable[[Callable[..., Any]], Callable[..., Any]]`
        A decorator that registers the decorated function as a handler for `exc_type`.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        ERROR_HANDLERS[exc_type] = func
        return func

    return decorator


def get_handler(error: Type[BaseException]) -> Optional[Callable[..., Any]]:
    chain: tuple[Type[BaseException], ...] = type(error).__mro__
    try:
        return next(filter(None, map(ERROR_HANDLERS.get, chain)))
    except StopIteration:
        return None


def get_message(ctx: SerenityContext, error: commands.CommandError) -> Optional[str]:
    handler = get_handler(error)  # type: ignore

    if handler is None:
        return

    return handler(ctx, error)


@register_handler(commands.CommandNotFound)
@register_handler(commands.CheckFailure)
@register_handler(commands.DisabledCommand)
def null_handler(
    ctx: SerenityContext,
    error: Union[
        commands.CommandNotFound, commands.CheckFailure, commands.DisabledCommand
    ],
) -> None:
    pass

@register_handler(commands.BadUnionArgument)
def bad_union_argument_handler(
    ctx: SerenityContext, error: commands.BadUnionArgument
) -> str:
    return str(error)

@register_handler(UserFeedbackException)
def user_feedback_handler(ctx: SerenityContext, error: UserFeedbackException) -> str:
    return error.to_string()


@register_handler(commands.CommandError)
def command_error_handler(ctx: SerenityContext, error: commands.CommandError) -> str:
    logger.exception("An unhandled exception occurred.", exc_info=error)
    return INTERNAL_ERROR


@register_handler(commands.ConversionError)
def conversion_error_handler(
    ctx: SerenityContext, error: commands.ConversionError
) -> str:
    converter = coverter_name(error.converter)
    logger.exception(
        "Unhandled conversion error occurred while converting %s.",
        converter,
        exc_info=error,
    )
    return INTERNAL_ERROR


@register_handler(commands.MissingRequiredArgument)
def missing_required_argument_handler(
    ctx: SerenityContext, error: commands.MissingRequiredArgument
) -> str:
    param, signature = get_raisable_context(ctx)
    return f"The `{param.name}` parameter is required.{signature}"


@register_handler(commands.TooManyArguments)
def too_many_arguments_handler(
    ctx: SerenityContext, error: commands.TooManyArguments
) -> str:
    return "Too many arguments were passed. Please check the command's usage."


@register_handler(commands.BadArgument)
def bad_argument_handler(ctx: SerenityContext, error: commands.BadArgument) -> str:
    error_message = str(error)
    param, signature = get_raisable_context(ctx)

    return f"Bad argument for `{param.name}`: {error_message}{signature}"


@register_handler(commands.MissingPermissions)
@register_handler(commands.BotMissingPermissions)
def bot_missing_permissions_handler(
    ctx: SerenityContext,
    error: Union[commands.BotMissingPermissions, commands.MissingPermissions],
) -> str:
    perms = error.missing_permissions

    if len(perms) <= 2:
        formatted = '` and `'.join(perms)
    else:
        formatted = '`, `'.join(perms[:-1]) + '`, and `' + perms[-1]

    s = 's' if len(perms) > 1 else ''
    missing = formatted.replace('_', ' ').replace('guild', 'server')

    your_or_me = (
        'I\'m' if isinstance(error, commands.BotMissingPermissions) else 'You\'re'
    )
    return f'{your_or_me} missing the `{missing}` permission{s} required to run this command.'


@register_handler(commands.UnexpectedQuoteError)
@register_handler(commands.InvalidEndOfQuotedStringError)
@register_handler(commands.ExpectedClosingQuoteError)
def quote_error_handler(
    ctx: SerenityContext,
    error: Union[
        commands.UnexpectedQuoteError,
        commands.InvalidEndOfQuotedStringError,
        commands.ExpectedClosingQuoteError,
    ],
) -> str:
    error_message = str(error)
    stop = "" if error_message.endswith(".") else "."
    return f'{error_message}{stop}'.replace('\'', '`')


@register_handler(commands.NoPrivateMessage)
def no_private_message_handler(
    ctx: SerenityContext, error: commands.NoPrivateMessage
) -> str:
    return "Sorry, I don't respond to commands in private messages."

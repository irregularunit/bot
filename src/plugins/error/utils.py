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

from re import sub
from typing import TYPE_CHECKING, Any, Callable, Tuple, Union

from discord.ext import commands

from src.shared import ExceptionFactory

if TYPE_CHECKING:
    from src.models.discord import SerenityContext

__all__: Tuple[str, ...] = (
    "INTERNAL_EXCEPTION",
    "converter_name",
    "get_failed_param",
    "get_raisable_context",
)

INTERNAL_EXCEPTION = ExceptionFactory.create_critical_exception(
    'An internal error occurred. Please contact the bot owner.'
).to_string()


def converter_name(converter: Union[Callable[..., Any], commands.Converter[Any]]) -> str:
    """
    Returns the name of a `commands.Converter`.

    Parameters
    ----------
    `converter : Union[Callable[..., Any], commands.Converter[Any]]`
        The converter to get the name of.

    Returns
    -------
    `str`
        The name of the converter.

    Notes
    -----
    This function is used internally in the Serenity bot framework to extract the name of a converter
    for error reporting and logging purposes.
    """
    return type(converter).__name__


def get_failed_param(ctx: SerenityContext) -> commands.Parameter:
    """
    Returns the parameter that failed to be converted in the context of the command invocation.

    Parameters
    ----------
    ctx : `SerenityContext`
        The context of the command invocation.

    Raises
    ------
    `commands.CommandError`
        If the command is not set in the context.

    Returns
    -------
    `commands.Parameter`
        The parameter that failed to be converted.
    """
    if ctx.command is None:
        raise commands.CommandError(INTERNAL_EXCEPTION)

    params = tuple(ctx.command.params.values())
    handles = (*ctx.args, *ctx.kwargs.values())

    return params[len(handles) - 2]


def get_raisable_context(ctx: SerenityContext) -> Tuple[commands.Parameter, str]:
    """
    Returns the parameter causing the error in the given command context and a formatted string of the command's signature.

    Parameters
    ----------
    ctx : `SerenityContext`
        The context object representing the context of the command that raised an error.

    Returns
    -------
    `Tuple[commands.Parameter, str]`
        A tuple containing the parameter causing the error and a formatted string of the command's signature.

    Raises
    ------
    `commands.CommandError`
        If the context has no associated command.

    Notes
    -----
    The parameter causing the error is determined by counting the number of arguments passed to the command that raised
    the error and selecting the corresponding parameter from the command's parameter list.

    The formatted string of the command's signature includes the name of the command, the usage of its parameters, and a
    usage instruction that users can follow to get more information about the command. The parameter causing the error
    is highlighted in the signature by surrounding it with bold formatting.

    Example
    -------
    Given the context `ctx` of a command that raised an error, the following code retrieves the parameter causing the
    error and a formatted string of the command's signature:

    >>> param, signature = get_raisable_context(ctx)
    ...
    """
    if ctx.command is None:
        raise commands.CommandError(INTERNAL_EXCEPTION)

    param = get_failed_param(ctx)

    name = ctx.command.qualified_name
    prefix = ctx.clean_prefix

    usage = sub(
        fr'(\s*[<\[]{param.name}[.=\w]*[>\]]\s*)',
        '`**`\u200b\\1\u200b`**`',
        ctx.command.signature,
    )
    usage = usage.rstrip('`') if usage.endswith('`') else f'{usage}`'

    signature = f'\n\nUsage: `{prefix}{name} {usage}\n' f"Type `{prefix}help {name}` for more information."

    return param, signature

from __future__ import annotations

import contextlib
import io
import time
from typing import TYPE_CHECKING, Annotated, Any, Optional, ClassVar

import discord
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.features.python import PythonFeature
from jishaku.flags import Flags
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor
from jishaku.repl.repl_builtins import get_var_dict_from_ctx

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None

from utils import BaseExtension

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context


class Jishaku(BaseExtension, *STANDARD_FEATURES, *OPTIONAL_FEATURES):
    if TYPE_CHECKING:
        bot: Bot

    __jsk_instance__: ClassVar[bool] = True

    async def jsk_python_result_handling(
        self,
        ctx: Context,
        result: Any,
        *,
        start_time: Optional[float] = None,
        redirect_stdout: Optional[str] = None,
    ):
        if isinstance(result, discord.Message):
            return await ctx.send(f"<Message <{result.jump_url}>>")

        elif isinstance(result, discord.File):
            return await ctx.send(file=result)

        elif isinstance(result, PaginatorInterface):
            return await result.send_to(ctx)

        elif isinstance(result, discord.Embed):
            return await ctx.send(embed=result)

        if not isinstance(result, str):
            result = repr(result)

        stripper = "**Redirected stdout**:\n{}"
        total = 2000
        if redirect_stdout:
            total -= len(f"{stripper.format(redirect_stdout)}\n")

        if len(result) <= total:
            if result.strip == "":
                result = "\u200b"

            if redirect_stdout:
                result = f"{stripper.format(redirect_stdout)}\n{result}"

            return await ctx.send(result.replace(self.bot.http.token or "", "[token omitted]"))

        if use_file_check(ctx, len(result)):
            # Discord's desktop and web client now supports an interactive file content
            # display for files encoded in UTF-8.
            # Since this avoids escape issues and is more intuitive than pagination for
            # long results, it will now be prioritized over PaginatorInterface if the
            # resultant content is below the filesize threshold
            return await ctx.send(file=discord.File(filename="output.py", fp=io.BytesIO(result.encode("utf-8"))))

        paginator = WrappedPaginator(prefix="```py", suffix="```", max_size=1985)

        if redirect_stdout:
            for chunk in self.bot.chunker(f'{stripper.format(redirect_stdout).replace("**", "")}\n', size=1975):
                paginator.add_line(chunk)

        for chunk in self.bot.chunker(result, size=1975):
            paginator.add_line(chunk)

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    @discord.utils.copy_doc(PythonFeature.jsk_python)
    @Feature.Command(parent="jsk", name="py", aliases=["python"])
    async def jsk_python(self, ctx: Context, *, argument: Annotated[Codeblock, codeblock_converter]) -> None:
        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict.update(
            self=self,
            _=self.last_result,
            _r=getattr(ctx.message.reference, 'resolved', None),
            _a=ctx.author,
            _m=ctx.message,
            _now=discord.utils.utcnow,
            _g=ctx.guild,
        )

        scope = self.scope  # type: ignore
        printed = io.StringIO()

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):  # type: ignore
                    with contextlib.redirect_stdout(printed):
                        executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                        start = time.perf_counter()

                        # Absolutely a garbage lib jesus christ.
                        async for send, result in AsyncSender(executor):  # type: ignore
                            self.last_result = result

                            value = printed.getvalue()
                            send(
                                await self.jsk_python_result_handling(
                                    ctx,
                                    result,
                                    start_time=start,
                                    redirect_stdout=None if value == "" else value,
                                )
                            )
        finally:
            scope.clear_intersection(arg_dict)


async def setup(bot: Bot) -> None:
    return await bot.add_cog(Jishaku(bot=bot))

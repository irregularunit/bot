import asyncio
import typing
from datetime import datetime
from uuid import UUID

T = typing.TypeVar('T')
P = typing.ParamSpec('P')
MaybeCoro = typing.Union[T, typing.Awaitable[T]]
MaybeCoroFunc = typing.Callable[P, 'MaybeCoro[T]']

async def null_callback(*args: typing.Any) -> typing.Tuple[typing.Any, ...]: ...
def wrap_func(func: typing.Any) -> typing.Any:
    """wrap in a coroutine"""
    ...

class Cron:
    def __init__(
        self,
        spec: str,
        func: MaybeCoroFunc[P, T] = ...,
        args: typing.Optional[typing.Tuple[typing.Any, ...]] = ...,
        start: typing.Optional[bool] = ...,
        uuid: typing.Optional[typing.Union[str, UUID]] = ...,
        loop: typing.Optional[asyncio.AbstractEventLoop] = ...,
        tz: typing.Optional[typing.Union[str, datetime, typing.Type[datetime], typing.Any]] = ...,
    ) -> None: ...
    def start(self) -> None:
        """Start scheduling"""
        ...
    def stop(self) -> None:
        """Stop scheduling"""
        ...
    async def next(self, *args: typing.Any) -> typing.Any:
        """yield from .next()"""
        ...
    def initialize(self) -> None:
        """Initialize croniter and related times"""
        ...
    def get_next(self) -> datetime:
        """Return next iteration time related to loop time"""
        ...
    def call_next(self) -> None:
        """Set next hop in the loop. Call task"""
        ...
    def call_func(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Called. Take care of exceptions using gather"""
        ...
    def set_result(self, result: typing.Any) -> None:
        """Set future's result if needed (can be an exception).
        Else raise if needed."""
        ...
    def __call__(self, func: MaybeCoroFunc[P, T]) -> typing.Self:
        """Used as a decorator"""
        ...
    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...

def crontab(
    spec: str,
    func: MaybeCoroFunc[P, T] = ...,
    args: typing.Any = (),
    start: typing.Optional[bool] = ...,
    loop: typing.Optional[asyncio.AbstractEventLoop] = ...,
    tz: typing.Optional[typing.Union[str, datetime, typing.Type[datetime], typing.Any]] = ...,
) -> Cron: ...

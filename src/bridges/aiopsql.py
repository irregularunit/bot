from contextlib import asynccontextmanager
from multiprocessing.managers import BaseManager

from types import TracebackType
from abc import ABC, abstractmethod
from collections import defaultdict
from logging import Logger, getLogger
from typing import Any, AsyncGenerator, Optional, Sequence, Type

from asyncpg import Pool, Record
from asyncpg.pool import PoolConnectionProxy
from asyncpg.transaction import Transaction

__all__: tuple[str, ...] = ("PostgresBridge",)


log: Logger = getLogger(__name__)


class ConnectionStragety(ABC):
    @abstractmethod
    async def acquire(self) -> ...:
        ...

    @abstractmethod
    async def release(self) -> ...:
        ...


class DefaultConnectionStragety(ConnectionStragety):
    __slots__: tuple[str, ...] = (
        "pool",
        "timeout",
        "_connection",
        "_transaction",
    )

    def __init__(self, pool: Pool, *, timeout: float = 10.0) -> None:
        self.pool: Pool = pool
        self.timeout: float = timeout

        self._connection: Optional[PoolConnectionProxy] = None
        self._transaction: Optional[Transaction] = None

    async def acquire(self) -> PoolConnectionProxy[Record]:
        return await self.__aenter__()
    
    async def release(self) -> None:
        await self.__aexit__(None, None, None)

    async def __aenter__(self) -> PoolConnectionProxy[Record]:
        self._connection = await self.pool.acquire(timeout=self.timeout)
        self._transaction = self._connection.transaction()
        await self._transaction.start()

        return self._connection
    
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        if exc_val and self._transaction is not None:
            log.warning("Rolling back transaction due to exception", exc_info=True)
            await self._transaction.rollback()

        if self._transaction is not None and not exc_val:
            await self._transaction.commit()

        if self._connection is not None:
            # Safe to release the connection 
            await self.pool.release(self._connection)


class PostgresManager:
    __slots__: tuple[str, ...] = ("stragety", "logger")

    def __init__(self, stragety: ConnectionStragety) -> None:
        self.stragety: ConnectionStragety = stragety
        self.logger: Logger = log.getChild("postgres")

    @asynccontextmanager
    async def acquire_connection(self) -> AsyncGenerator[PoolConnectionProxy[Record], None]:
        connection: PoolConnectionProxy[Record] = await self.stragety.acquire()
        try:
            yield connection
        finally:
            await self.stragety.release()


    async def execute(
        self,
        query: str,
        *args: Any,
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> None:
        async with self.acquire_connection() as connection:
            await connection.execute(query, *args, timeout=timeout, **kwargs)

    async def fetch(
        self,
        query: str,
        *args: Any,
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> Record | list[Record]:
        async with self.acquire_connection() as connection:
            return await connection.fetch(query, *args, timeout=timeout, **kwargs)
        
    async def fetchone(
        self,
        query: str,
        *args: Any,
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> Record | None:
        async with self.acquire_connection() as connection:
            return await connection.fetchrow(query, *args, timeout=timeout, **kwargs)

    async def executemany(
        self,
        query: str,
        args: Sequence[Any],
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> None:
        async with self.acquire_connection() as connection:
            return await connection.executemany(query, args, timeout=timeout, **kwargs)
        
    async def tablesummary(self, table: str) -> dict[str, dict[str, str]]:
        tables: dict[str, dict[str, str]] = defaultdict(dict)

        async with self.acquire_connection() as connection:
            async for record in connection.cursor(
                """
                SELECT * FROM information_schema.columns
                WHERE $1::TEXT IS NULL OR table_name = $1::TEXT
                ORDER BY
                table_schema = 'pg_catalog',
                table_schema = 'information_schema',
                table_catalog,
                table_schema,
                table_name,
                ordinal_position
                """,
                table,
            ):
                table_name: str = f"{record['table_schema']}.{record['table_name']}"
                tables[table_name][record["column_name"]] = str(record["data_type"]).upper() + (
                    " NOT NULL" if record["is_nullable"] == "NO" else ""
                )

        return tables


class PostgresBridge(BaseManager):
    __slots__: tuple[str, ...] = ("pool", "timeout",)

    def __init__(self, pool: Pool, *, timeout: float = 10.0) -> None:
        super().__init__(DefaultConnectionStragety(pool, timeout=timeout))

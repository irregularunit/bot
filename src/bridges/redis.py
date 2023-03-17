import asyncio
import uuid

from logging import Logger, getLogger
from typing import Any, Optional

from redis.asyncio import Redis, ConnectionPool, RedisError


__all__: tuple[str, ...] = ("RedisBridge",)


log: Logger = getLogger(__name__)


def check_running(func: Any) -> Any:
    async def wrapper(self, *args, **kwargs) -> Any:
        if not self._is_stopping:
            return False
        return await func(self, *args, **kwargs)
    return wrapper


class RedisBridge:
    __slots__: tuple[str, ...] = (
        "_loop",
        "_pool",
        "_redis",
        "_is_connected",
        "_is_stopping",
        "_need_execution",
        "log",
    )

    def __init__(
        self,
        *,
        uri: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self._pool: ConnectionPool = ConnectionPool.from_url(uri)
        self._redis: Redis = Redis(connection_pool=self._pool)

        self.log: Logger = log.getChild("redis")

        self._is_connected = False
        self._is_stopping = False
        self._need_execution = set()

    @property
    def client(self) -> Redis:
        return self._redis
    
    @property
    def connection(self) -> ConnectionPool:
        return self._pool
    
    @property
    def is_stopping(self) -> bool:
        return self._is_stopping
    
    async def connect(self) -> None:
        if self._is_connected:
            log.warning("Redis connection already established, skipping...")
            return
        
        while not self._is_connected:
            try:
                self._redis = await self._redis.initialize()
                self._is_connected: bool = True
                log.info("Successfully established connection to Redis")
                break
            except RedisError:
                log.warning("Redis connection failed, retrying in 5 seconds...")
                await asyncio.sleep(1)

    @classmethod
    def setup_redis(cls, uri: str) -> "RedisBridge":
        return cls(uri=uri)

    def lock(self, key: str) -> None:
        return self._need_execution.add(key)
    
    def unlock(self, key: str) -> None:
        try:
            self._need_execution.discard(key)
        except ValueError:
            pass

    def stringify(self, data: Any) -> str:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
            data = "b2dntcode_" + data
        elif isinstance(data, int):
            data = str(data)

        return data
        
    def to_original(self, data: Optional[bytes]) -> Optional[Any]:
        if not data:
            return None
        
        parsed: str = data.decode("utf-8")

        try:
            return float(parsed)
        except ValueError:
            pass

        if parsed.isdigit():
            return int(parsed, 10)
        if parsed.startswith("b2dntcode_"):
            return parsed[10:].encode("utf-8")
        
        return parsed
    
    async def close(self) -> None:
        _log: Logger = self.log.getChild("close")
        _log.info("Closing connection, waiting for %s tasks...", len(self._need_execution))
        current_timeout: float = 0.0

        while len(self._need_execution) > 0:
            await asyncio.sleep(0.2)

            if len(self._need_execution) < 1:
                break
            if current_timeout > 10.0:
                _log.info("Timeout reached, closing connection anyway!")
                break

            current_timeout += 0.2
        self._is_stopping: bool = True

        await self._redis.close()
        await self._pool.disconnect()

        _log.info("Redis connection has been terminated")

    def acquire_lock(self, name: str) -> str:
        uniq_id: str = str(uuid.uuid4())
        self.lock(f"{name}_" + uniq_id)

        return uniq_id
    
    def release_lock(self, name: str, uniq_id: str) -> None:
        self.unlock(f"{name}_" + uniq_id)
    
    async def get(self, key: str, fallback: Any = None) -> Any:
        if self._is_stopping:
            return None
        
        uniq_id: str = self.acquire_lock("get")

        try:
            res = await self._redis.get(key)
            res: Any | None = self.to_original(res)

            if res is None:
                res = fallback
                
        except RedisError:
            res = fallback

        self.release_lock("get", uniq_id)

        return res
    
    @check_running
    async def set(self, key: str, data: Any) -> Optional[bool]:
        uniq_id: str = self.acquire_lock("set")

        try:
            res: bool | None = await self._redis.set(key, self.stringify(data))
        except RedisError:
            res = False

        self.release_lock("set", uniq_id)

        return res
    
    @check_running
    async def setex(self, key: str, data: Any, expires: int) -> bool:
        uniq_id: str = self.acquire_lock("setex")

        try:
            res: bool = await self._redis.setex(key, expires, self.stringify(data))
        except RedisError:
            res = False

        self.release_lock("setex", uniq_id)

        return res

    @check_running
    async def exists(self, key: str) -> bool:
        uniq_id: str = self.acquire_lock("exists")

        try:
            res: int = await self._redis.exists(key)
        except RedisError:
            res = False

        self.release_lock("exists", uniq_id)

        return bool(res)
    
    @check_running
    async def rm(self, key: str) -> bool:
        uniq_id: str = self.acquire_lock("rm")

        try:
            res: int = await self._redis.delete(key)
        except RedisError:
            res = 0

        self.release_lock("rm", uniq_id)

        return bool(res)

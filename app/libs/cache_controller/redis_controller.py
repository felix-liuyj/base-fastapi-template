from typing import Optional

from redis.asyncio.client import Redis
from redis.asyncio.cluster import RedisCluster

from app.libs.cache_controller import BaseCacheController

__all__ = (
    'RedisCacheController',
)


class RedisCacheController(BaseCacheController):

    def __init__(self):
        super().__init__()
        self.redis: Redis[bytes] | RedisCluster[bytes] = self.cache.redis

    async def get_with_ttl(self, key: str) -> tuple[int, str]:
        return await self.cache.get_with_ttl(key)

    async def info(self) -> dict:
        return await self.redis.info()

    async def get(self, key: str) -> Optional[str]:
        return await self.cache.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        return await self.cache.set(key, value, expire=expire)

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        return await self.cache.clear(namespace, key)

    async def check_email_v_code(self, email: str, v_code: str) -> bool:
        v_code_from_redis = await self.get(f'{email}-verification-code')
        return v_code == v_code_from_redis

    async def increment_redis_count_with_item(self, name: str, item: str, increment: int = 1):
        await self.redis.zincrby(name, increment, item)

    async def increment_redis_count_sequence(self, name: str, sequence: list, increment: int = 1):
        for item in sequence:
            await self.redis.zincrby(name, increment, item)

    async def get_redis_count_tops(self, name: str, limit: int = 10, start: int = 0) -> list:
        """获取访问量最高的 IP"""
        return await self.redis.zrevrange(name, start, limit - 1, withscores=True)

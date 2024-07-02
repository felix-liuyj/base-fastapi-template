from typing import Optional

from fastapi_cache.backends.redis import RedisBackend

from app.libs.cache_controller import BaseCacheController

__all__ = (
    'RedisCacheController',
)


class RedisCacheController(BaseCacheController):

    def __init__(self):
        super().__init__()
        self.backend: RedisBackend = None

    async def get_with_ttl(self, key: str) -> tuple[int, str]:
        return await self.backend.get_with_ttl(key)

    async def get(self, key: str) -> Optional[str]:
        return await self.backend.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        return await self.backend.set(key, value, expire=expire)

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        return await self.backend.clear(namespace, key)

    async def check_email_v_code(self, email: str, v_code: str) -> bool:
        v_code_from_redis = await self.get(f'{email}-verification-code')
        return v_code == v_code_from_redis

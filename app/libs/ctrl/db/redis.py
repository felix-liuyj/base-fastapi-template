from redis.asyncio.client import Redis

from app.config import get_settings

__all__ = (
    'RedisCacheController',
)


class RedisCacheController(Redis):
    def __init__(self):
        super().__init__(
            host=get_settings().REDIS_HOST, port=get_settings().REDIS_PORT, ssl=False,
            username=get_settings().REDIS_USERNAME, password=get_settings().REDIS_PASSWORD,
            encoding="utf-8", decode_responses=True
        )

    async def __aenter__(self):
        return self

    async def check_email_v_code(self, email: str, v_code: str) -> bool:
        v_code_from_redis = await self.get(f'{email}-verification-code')
        return v_code == v_code_from_redis

    async def increment_redis_count_with_item(self, name: str, item: str, increment: int = 1):
        await self.zincrby(name, increment, item)

    async def increment_redis_count_with_sequence(self, name: str, sequence: list | set, increment: int = 1):
        for item in sequence:
            await self.zincrby(name, increment, item)

    async def get_redis_count_tops(self, name: str, limit: int = 10, start: int = 0) -> list:
        """获取访问量最高的 IP"""
        return await self.zrevrange(name, start, limit - 1, withscores=True)

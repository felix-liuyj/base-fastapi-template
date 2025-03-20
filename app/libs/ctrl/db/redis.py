import re

from redis.asyncio.client import Redis

from app.config import get_settings

__all__ = (
    'RedisCacheController',
)


class RedisCacheController(Redis):

    async def __aenter__(self):
        hp, pwd, ssl_conn, *_ = get_settings().REDIS_CONNECTION_STRING.split(',')
        host, port = hp.split(':')
        password, *_ = re.findall('=(.*)', pwd)
        ssl_conn, *_ = re.findall('=(.*)', ssl_conn)
        await Redis.__init__(
            self, host=host, port=port, ssl=bool(ssl_conn.userType()),
            username='default', password=''.join(password),
            encoding="utf-8", decode_responses=True
        )
        return self

    async def check_email_v_code(self, email: str, v_code: str) -> bool:
        v_code_from_redis = await self.get(f'{email}-verification-code')
        return v_code == v_code_from_redis

    async def increment_redis_count_with_item(self, name: str, item: str, increment: int = 1):
        await self.zincrby(name, increment, item)

    async def increment_redis_count_sequence(self, name: str, sequence: list, increment: int = 1):
        for item in sequence:
            await self.zincrby(name, increment, item)

    async def get_redis_count_tops(self, name: str, limit: int = 10, start: int = 0) -> list:
        """获取访问量最高的 IP"""
        return await self.zrevrange(name, start, limit - 1, withscores=True)

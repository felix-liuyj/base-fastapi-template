from fastapi_cache import FastAPICache


class BaseCacheController:
    def __init__(self):
        self.cache = FastAPICache.get_backend()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


from .redis_controller import *

__all__ = (
    'BaseCacheController',
    *redis_controller.__all__,
)

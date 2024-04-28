from fastapi_cache import FastAPICache


class BaseCacheController:
    def __init__(self):
        self.backend = None

    async def __aenter__(self):
        self.backend = FastAPICache.get_backend()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


from .redis_controller import *

__all__ = (
    'BaseCacheController',
    *redis_controller.__all__,
)

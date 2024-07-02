import os
import pathlib
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import RedisCluster, Redis
from redis.asyncio.cluster import ClusterNode
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.libs.kafka import BaseConsumer
from app.libs.custom import cus_print
from app.models import BaseDBModel

__all__ = (
    'create_app',
)


def create_app():
    app = FastAPI(lifespan=lifespan)
    statis_path = f'{pathlib.Path(__file__).resolve().parent}/statics'
    if not os.path.exists(statis_path):
        os.mkdir(statis_path)
    app.mount("/statics", StaticFiles(directory=statis_path), name="statics")
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    await register_routers(app)
    mongo_client = await initialize_mongodb_client()
    await init_db(mongo_client)
    if get_settings().KAFKA_CLUSTER_BROKERS:
        async with BaseConsumer():
            print("Startup complete")
            yield
    else:
        yield
    mongo_client.close()
    print("Shutdown complete")


async def init_cache():
    if get_settings().REDIS_CLUSTER_NODE:
        redis = RedisCluster(
            startup_nodes=[ClusterNode(host=host, port=port) for host, port in [
                node_config.split(':') for node_config in get_settings().REDIS_CLUSTER_NODE.split(',')
            ]],
            username=get_settings().REDIS_USERNAME, password=get_settings().REDIS_PASSWORD,
            encoding="utf-8", decode_responses=True
        )
    else:
        redis = Redis(
            host=get_settings().REDIS_HOST, port=get_settings().REDIS_PORT,
            username=get_settings().REDIS_USERNAME, password=get_settings().REDIS_PASSWORD,
            encoding="utf-8", decode_responses=True
        )
    FastAPICache.init(
        RedisBackend(redis),
        prefix=f'{"-".join(get_settings().APP_NAME.split(" "))}-{get_settings().APP_ENV}-cache'
    )


async def register_routers(app: FastAPI):
    from app.api import router as root_router
    from app.api.common import router as main_router

    app.include_router(root_router)
    app.include_router(main_router)


async def initialize_mongodb_client():
    return AsyncIOMotorClient(
        host=get_settings().MONGODB_URI,
        port=get_settings().MONGODB_PORT,
        username=get_settings().MONGODB_USERNAME,
        password=get_settings().MONGODB_PASSWORD,
        authSource=get_settings().MONGODB_AUTHENTICATION_SOURCE
    )


async def init_db(mongo_client: AsyncIOMotorClient):
    import app.models.user as user_models
    await init_beanie(
        database=getattr(mongo_client, get_settings().MONGODB_DB),
        document_models=[
            *load_models_class(user_models),
        ]
    )


def load_models_class(module):
    class_list = []
    for model in module.__all__:
        module_class = getattr(module, model)
        if module_class and issubclass(module_class, BaseDBModel):
            class_list.append(module_class)

    return class_list

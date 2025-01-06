import os
import pathlib
import re
from contextlib import asynccontextmanager

from beanie import init_beanie
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message
from app.libs.custom import cus_print
from app.libs.sso import SSOProviderEnum
from app.models import BaseDBModel
from app.response import ResponseModel

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
        allow_origins=['*'],
        allow_methods=['*'],
        allow_headers=['*'],
        expose_headers=['*']
    )
    register_http_exception_handlers(app)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Check Encrypt Key...')
    if not get_settings().ENCRYPT_KEY:
        cus_print(f'Encrypt Key: {Fernet.generate_key().decode("utf-8")}, Please save it in config file', 'p')
    print('Load Core Application...')
    await init_cache()
    await register_routers(app)
    mongo_client = AsyncIOMotorClient(get_settings().COSMOS_DB_CONNECTION_STRING)
    await init_db(mongo_client)
    print("Startup complete")
    yield
    mongo_client.close()
    print("Shutdown complete")


async def init_cache():
    hp, pwd, ssl_conn, *_ = get_settings().REDIS_CONNECTION_STRING.split(',')
    host, port = hp.split(':')
    password, *_ = re.findall('=(.*)', pwd)
    ssl_conn, *_ = re.findall('=(.*)', ssl_conn)
    redis = Redis(
        host=host, port=port, ssl=bool(ssl_conn.title()),
        username='default', password=''.join(password),
        encoding="utf-8", decode_responses=True
    )
    FastAPICache.init(
        RedisBackend(redis),
        prefix=f'{"-".join(get_settings().APP_NAME.split(" "))}-{get_settings().APP_ENV}-cache'
    )


async def register_routers(app: FastAPI):
    from app.api import router as root_router
    from app.api.account import router as account_router

    app.include_router(root_router)
    app.include_router(account_router)


async def init_db(mongo_client: AsyncIOMotorClient):
    import app.models.account as user_models
    await init_beanie(
        database=getattr(mongo_client, get_settings().COSMOS_DB_NAME),
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


def register_http_exception_handlers(app: FastAPI):
    # 定义全局异常处理器，用于捕获 401 错误并重定向到 SSO 登录页面
    app.add_exception_handler(401, custom_http_exception_handler)


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith('/admin'):
        from app.libs.sso.azure import generate_sso_login_url
    else:
        from app.libs.sso.hktdc import generate_sso_login_url
    return RedirectResponse(await generate_sso_login_url())

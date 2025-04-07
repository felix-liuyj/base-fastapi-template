import os
import pathlib
import time
from contextlib import asynccontextmanager
from inspect import isclass

from beanie import init_beanie
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED

from app.config import Settings, get_settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message
from app.libs.custom import cus_print
from app.libs.sso import SSOProviderEnum
from app.models import BaseDatabaseModel
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
    register_middlewares(app)
    register_http_exception_handlers(app)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Check Env Config:')
    print(dict(get_settings()))
    print('Check Encrypt Key...')
    if not get_settings().ENCRYPT_KEY:
        cus_print(f'Encrypt Key: {Fernet.generate_key().decode("utf-8")}, Please save it in config file', 'p')
    print('Load Core Application...')
    await register_routers(app)
    mongo_client = await initialize_mongodb_client()
    await init_db(mongo_client)
    print("Startup complete")
    yield
    mongo_client.close()
    print("Shutdown complete")


def register_middlewares(app: FastAPI):
    @app.middleware("http")
    async def log_request_time(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        print(f'Request {request.url} took {duration:.2f}s')
        return response


async def register_routers(app: FastAPI):
    from app.api import router as root_router
    from app.api.account import router as account_router

    app.include_router(root_router)
    app.include_router(account_router)


async def initialize_mongodb_client():
    return AsyncIOMotorClient(
        host=get_settings().MONGODB_URI,
        port=get_settings().MONGODB_PORT,
        username=get_settings().MONGODB_USERNAME,
        password=get_settings().MONGODB_PASSWORD,
        authSource=get_settings().MONGODB_AUTHENTICATION_SOURCE
    )


async def init_db(mongo_client: AsyncIOMotorClient):
    import app.models.account as user_models
    await init_beanie(
        database=getattr(mongo_client, get_settings().MONGODB_DB),
        document_models=[
            *load_models_class(user_models),
        ]
    )
    print('Database Test...')
    await test_models_class(load_models_class(user_models))
    print('Database Init Complete', end='\n\n')


async def test_models_class(module):
    for model in module:
        await model.find().to_list()
        print(f'{model.__name__} test passed')


def load_models_class(module):
    class_list = []
    for model in module.__all__:
        module_class = getattr(module, model)
        if module_class and isclass(module_class) and issubclass(module_class, BaseDatabaseModel):
            class_list.append(module_class)

    return class_list


def register_http_exception_handlers(app: FastAPI):
    # 定义全局异常处理器，用于捕获 401 错误并重定向到 SSO 登录页面
    app.add_exception_handler(HTTP_401_UNAUTHORIZED, custom_un_auth_exception_handler)
    # 定义全局异常处理器，用于捕获 403 错误并重定向到 SSO 登录页面
    app.add_exception_handler(HTTP_403_FORBIDDEN, custom_auth_forbidden_exception_handler)
    # 定义全局异常处理器，用于捕获 422 错误（请求参数验证失败）
    app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)
    # 定义全局异常处理器，用于捕获 500 错误（服务器内部错误）
    app.add_exception_handler(HTTP_500_INTERNAL_SERVER_ERROR, custom_internal_server_exception_handler)


async def custom_un_auth_exception_handler(request: Request, exc: HTTPException):
    print(f'custom_http_exception_handler: {exc.detail}')
    if request.url.path.startswith('/admin'):
        return JSONResponse(content={
            'category': '00',
            'code': ResponseStatusCodeEnum.UNAUTHORIZED,
            'message': get_response_message(ResponseStatusCodeEnum.UNAUTHORIZED),
            'data': f'admin exception: {exc.detail}'
        })
    return JSONResponse(content={
        'category': '00',
        'code': ResponseStatusCodeEnum.UNAUTHORIZED.value,
        'message': get_response_message(ResponseStatusCodeEnum.UNAUTHORIZED),
        'data': f'normal exception: {exc.detail}'
    })


async def custom_auth_forbidden_exception_handler():
    return RedirectResponse('https://hkfilmart.hktdc.com/conference/hkfilmart/en')


async def custom_validation_exception_handler(exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            'category': '00',
            'code': ResponseStatusCodeEnum.ILLEGAL_PARAMETERS.value,
            'message': get_response_message(ResponseStatusCodeEnum.ILLEGAL_PARAMETERS),
            'data': [f'{" → ".join(map(str, error.get("loc")))}: {error.get("msg")}' for error in exc.errors()]
        }
    )


async def custom_internal_server_exception_handler(exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={
            'category': '00',
            'code': ResponseStatusCodeEnum.SYSTEM_ERROR.value,
            'message': get_response_message(ResponseStatusCodeEnum.SYSTEM_ERROR),
            'data': str(exc)
        }
    )

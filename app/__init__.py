import json
import logging
import os
import pathlib
import time
from contextlib import asynccontextmanager

from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED

from app.config import Settings, get_settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message
from app.libs.ctrl.db.mongodb import initialize_database
from app.libs.custom import cus_print
from app.libs.sso import SSOProviderEnum
from app.response import ResponseModel

__all__ = (
    'lifespan',
    'initial_logger',
    'register_middlewares',
    'register_http_exception_handlers',
)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # 如果传入的是 dict，会自动 dump 成 JSON 字符串
        if isinstance(record.msg, dict):
            record.msg = json.dumps(record.msg, ensure_ascii=False)
        return super().format(record)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    :param app:
    :return:
    """
    print(app.routes)
    print('Check Env Config:')
    print(dict(get_settings()))
    print('Check Encrypt Key...')
    if not get_settings().ENCRYPT_KEY:
        cus_print(f'Encrypt Key: {Fernet.generate_key().decode("utf-8")}, Please save it in config file', 'p')
    print('Load Core Application...')
    client = await initialize_database()
    print("Startup complete")
    yield
    if client:
        client.close()
    print("Shutdown complete")


def register_middlewares(app: FastAPI, logger: logging.Logger = None):
    @app.middleware("http")
    async def log_request_time(request: Request, call_next):
        start_time = time.time()
        # 请求信息
        request_body = await request.body()
        request_headers = dict(request.headers)

        # 执行请求
        response: Response = await call_next(request)
        if request.url.path == '/status':
            return response

        # 构造日志内容
        log_data = {
            "path": request.url.path, "method": request.method,
            "query_params": dict(request.query_params),
            "request_body": request_body.decode("utf-8", errors="ignore"),
            "request_headers": request_headers,
            "status_code": response.status_code,
            "process_time_ms": (time.time() - start_time) * 1000,
        }
        logger.info(log_data)
        return response


def initial_logger(logger: logging.Logger) -> logging.Logger:
    logger.setLevel(logging.INFO)

    # 创建日志目录
    log_dir = f'{pathlib.Path(__file__).resolve().parent}/statics/logs'
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, 'api-requests.log')
    handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')

    formatter = JsonFormatter('%(message)s')  # 只打印 JSON 内容
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False  # 不传给上层的 uvicorn logger

    return logger


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

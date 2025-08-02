import logging
import os
import pathlib

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app import lifespan, initial_logger, register_middlewares, register_http_exception_handlers
from app.api import router as root_router
from app.api.account import router as account_router

logger = logging.getLogger("api.requests")

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
initial_logger(logger)
register_middlewares(app, logger)
register_http_exception_handlers(app)

app.include_router(root_router, prefix='', tags=['Root API'], dependencies=[])
app.include_router(account_router, prefix='/account', tags=['Account API'], dependencies=[])

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

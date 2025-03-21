from asyncio import sleep
from typing import TypeVar

from starlette.responses import StreamingResponse

from app.response import ResponseModel

__all__ = (
    'create_response',
    'create_event_stream_response',
)

VMT = TypeVar("VMT", bound="BaseViewModel")


async def create_response(view_model: VMT, *args, response_handler: callable = None, **kwargs) -> ResponseModel:
    async with view_model(*args, **kwargs) as response:
        return response_handler(response) if response_handler else response


async def create_event_stream_response(view_model: VMT, *args, **kwargs) -> StreamingResponse:
    async def event_stream():
        while True:
            async with view_model(*args, **kwargs) as response:
                yield f'data: {response.model_dump_json()}\n\n'
            await sleep(5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

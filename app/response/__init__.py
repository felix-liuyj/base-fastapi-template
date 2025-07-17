from asyncio import sleep
from typing import Generic
from typing import TypeVar

from pydantic import Field, BaseModel
from starlette.responses import StreamingResponse

from app.config import get_settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message

T = TypeVar('T')

__all__ = (
    'ResponseModel',
    'IllegalParametersResponseModel',
    'InternalServerErrorResponseModel',
    'create_response',
    'create_event_stream_response',
)

VMT = TypeVar("VMT", bound="BaseViewModel")
PGItemT = TypeVar('PGItemT')


class ResponseModel(BaseModel, Generic[T]):
    category: str = Field(
        ..., description='Platform Identifier, only 00 for the whole Filmart Online Platform', examples=['00']
    )
    code: ResponseStatusCodeEnum = Field(
        ..., description='Custom Response Code', examples=[ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY]
    )
    message: str = Field(..., description='Response Message', examples=['Operating Successfully'])
    data: T = Field(..., description='Response data')


class BasePaginationResponseDataType(BaseModel, Generic[PGItemT]):
    total: int = Field(..., description='Total number of items')
    pageNo: int = Field(..., description='Current page number')
    pageSize: int = Field(..., description='Number of items per page')
    hasMore: bool = Field(..., description='Whether there is a next page')
    items: list[PGItemT] = Field(..., description='List of items on the current page')


class IllegalParametersResponseModel(ResponseModel[list[str]]):
    data: list[str] = Field(..., description='Response data', examples=[["query → errorFieldName: Error message"]])

    class Config:
        schema_extra = {
            'examples': [
                {
                    'category': get_settings().APP_NO,
                    'code': ResponseStatusCodeEnum.ILLEGAL_PARAMETERS.value,
                    'message': get_response_message(ResponseStatusCodeEnum.ILLEGAL_PARAMETERS),
                    'data': ["query → errorFieldName: Error message"]
                }
            ]
        }


class InternalServerErrorResponseModel(ResponseModel[str]):
    data: str = Field(..., description='Response data', examples=['Internal Server Error'])

    class Config:
        schema_extra = {
            'examples': [
                {
                    'category': get_settings().APP_NO,
                    'code': ResponseStatusCodeEnum.SYSTEM_ERROR.value,
                    'message': get_response_message(ResponseStatusCodeEnum.SYSTEM_ERROR),
                    'data': 'Detail error message'
                }
            ]
        }


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

from typing import Generic, TypeVar

from pydantic import Field, BaseModel

from app.config import get_settings
from app.libs.constants import ResponseStatusCodeEnum, get_response_message

T = TypeVar('T')

__all__ = (
    'ResponseModel',
    'IllegalParametersResponseModel',
    'InternalServerErrorResponseModel',
)


class ResponseModel(BaseModel, Generic[T]):
    category: str = Field(
        ..., description='Platform Identifier, only 00 for the whole Filmart Online Platform', examples=['00']
    )
    code: ResponseStatusCodeEnum = Field(
        ..., description='Custom Response Code', examples=[ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY]
    )
    message: str = Field(..., description='Response Message', examples=['Operating Successfully'])
    data: T = Field(..., description='Response data')


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

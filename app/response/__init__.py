from typing import Generic, TypeVar

from pydantic import Field, BaseModel

T = TypeVar('T')

__all__ = (
    'ResponseModel',
)


class ResponseModel(BaseModel, Generic[T]):
    category: str = Field(..., description='Response Of Platform')
    code: str = Field(..., description='Custom Response Code')
    message: str = Field(..., description='Response Message')
    data: T = Field(..., description='Response data')

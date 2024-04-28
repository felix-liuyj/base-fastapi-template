from enum import Enum
from functools import lru_cache
from typing import List

from pydantic.dataclasses import dataclass

__all__ = (
    'ApiResponse',
    'ResponseStatusCodeEnum',
    'ResponseMessageMap',
    'get_response_message',
)


@dataclass
class ApiResponse:
    category: str
    code: str
    message: str
    data: List[dict] | dict


class ResponseStatusCodeEnum(Enum):
    OPERATING_SUCCESSFULLY = '0000'
    EMPTY_CONTENT = '0001'
    NOTHING_CHANGED = '0002'
    OPERATING_FAILED = '2000'
    ILLEGAL_PARAMETERS = '2001'
    UNAUTHORIZED = '2002'
    FORBIDDEN = '2003'
    NOT_FOUND = '2004'
    METHOD_NOT_ALLOWED = '2005'
    REQUEST_TIMEOUT = '2006'
    SYSTEM_ERROR = '3000'


class ResponseMessageMap:
    OPERATING_SUCCESSFULLY = "Operating successfully"
    EMPTY_CONTENT = "Empty Content"
    NOTHING_CHANGED = "Nothing Changed"
    OPERATING_FAILED = "Operating Failed"
    ILLEGAL_PARAMETERS = "Illegal Parameters"
    UNAUTHORIZED = "Unauthorized"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not Found"
    METHOD_NOT_ALLOWED = "Method Not Allowed"
    REQUEST_TIMEOUT = "Request Timeout"
    SYSTEM_ERROR = "System Error"


@lru_cache()
def get_response_message(status_code: ResponseStatusCodeEnum | str):
    rm_map = ResponseMessageMap()
    if isinstance(status_code, ResponseStatusCodeEnum):
        return getattr(rm_map, status_code.name, 'Undefined status code')
    status_code_enum = ResponseStatusCodeEnum(status_code)
    return getattr(rm_map, status_code_enum.name, status_code)


if __name__ == '__main__':
    print(get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY))

from enum import Enum

from fastapi import HTTPException
from starlette import status

__all__ = (
    'SSOProviderEnum',
    'generate_un_auth_exception',
)


class SSOProviderEnum(Enum):
    HKTDC = 'hktdc'
    AZURE = 'azure'


def generate_un_auth_exception(msg: str, provider: SSOProviderEnum) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=msg, headers={
            "Authenticate": "Bearer", "provider": provider
        }
    )

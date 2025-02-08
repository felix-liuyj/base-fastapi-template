from enum import Enum

from fastapi import HTTPException
from fastapi import Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.security.utils import get_authorization_scheme_param
from starlette import status

__all__ = (
    'SSOProviderEnum',
    'generate_un_auth_exception',
    'OptionalOAuth2AuthorizationCodeBearer',
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


class OptionalOAuth2AuthorizationCodeBearer(OAuth2AuthorizationCodeBearer):
    async def __call__(self, request: Request) -> str | None:
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return None
        return param

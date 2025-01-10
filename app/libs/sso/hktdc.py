import uuid
from typing import Optional

import httpx
from fastapi import Depends
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import decode as jwt_decode, InvalidTokenError, get_unverified_header, algorithms, PyJWTError
from pydantic import BaseModel, Field

from app.config import get_settings
from app.libs.cache import RedisCacheController
from app.libs.sso import SSOProviderEnum
from app.models.account import UserProfile

__all__ = (
    'oauth2_scheme',
    'parse_oauth_jwt',
    'get_user_profile',
    'generate_sso_login_url',
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{get_settings().SSO_HKTDC_BASE_URL}/uaa/oauth2/authorize",
    tokenUrl=f"{get_settings().SSO_HKTDC_BASE_URL}/uaa/oauth2/token"
)


class TokenData(BaseModel):
    aud: str
    azp: str
    email: str
    exp: int
    familyName: str = Field(..., alias='family_name')
    givenName: str = Field(..., alias='given_name')
    iat: int
    iss: str
    sub: str
    updated_at: Optional[str] = Field(None, alias="updatedAt")


async def generate_sso_login_url() -> str:
    import uuid
    from app.libs.cache import RedisCacheController

    state = uuid.uuid4()
    request_id = uuid.uuid4()
    async with RedisCacheController() as cache:
        await cache.set(str(state), str(request_id), 60 * 5)
    return (
        f'{get_settings().SSO_HKTDC_BASE_URL}/uaa/oauth2/authorize?'
        f'response_type=code&'
        f'client_id={get_settings().SSO_HKTDC_CLIENT_ID}&'
        f'redirect_uri={str(get_settings().SSO_HKTDC_REDIRECT_URI)}&'
        f'x_request_id={request_id}&'
        f'scope=openid /v2/shared-services/management/user-profile.readonly&'
        f'state={state}'
    )


# 验证 JWT ID 令牌
async def parse_oauth_jwt(id_token: str, need_login: bool = True) -> TokenData | None:
    from app.libs.sso import generate_un_auth_exception
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{get_settings().SSO_HKTDC_BASE_URL}/uaa/oidc/jwks')
        jwks = response.json()
    public_key, *_ = jwks.get("keys", [])

    try:
        # 解码 JWT Header 以提取 'kid'
        unverified_header = get_unverified_header(id_token)
        if unverified_header.get('kid') != public_key.get('kid'):
            raise generate_un_auth_exception('invalid token', SSOProviderEnum.HKTDC)

        # 验证并解码 JWT
        decoded_token = jwt_decode(
            id_token, algorithms.RSAAlgorithm.from_jwk(public_key),  # 获取与 kid 匹配的公钥
            algorithms=["RS256"], audience=get_settings().SSO_HKTDC_CLIENT_ID
        )
        return TokenData.model_validate(decoded_token)
    except InvalidTokenError as e:
        print(f"Invalid token: {e}")
        if not need_login:
            return
        raise generate_un_auth_exception('invalid token', SSOProviderEnum.HKTDC)


async def get_user_profile(token: str = Depends(oauth2_scheme)) -> UserProfile | None:
    from app.libs.sso import generate_un_auth_exception
    try:
        async with RedisCacheController() as cache:
            if not (email := await cache.get(token)):
                raise generate_un_auth_exception('invalid token')
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_settings().SSO_HKTDC_BASE_URL}/shared-services/management/user-profiles",
                params={"queryType": "by_email", "email": email},
                headers={
                    "Authorization": f"Bearer {token}",
                    "x-api-key": get_settings().SSO_HKTDC_API_KEY,
                    "Content-Type": "application/json",
                    "x-request-id": f'ORS-{uuid.uuid4()}',
                }
            )
            response_data = response.raise_for_status().json()
        return UserProfile.model_validate(response_data)
    except httpx.HTTPStatusError as e:
        raise generate_un_auth_exception("Token validation failed", SSOProviderEnum.HKTDC)
    except PyJWTError as e:
        raise generate_un_auth_exception("Invalid token", SSOProviderEnum.HKTDC)

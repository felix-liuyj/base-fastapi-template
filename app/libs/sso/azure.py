import uuid
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel, ValidationError, Field, EmailStr

from app.config import get_settings
from app.libs.cache import RedisCacheController
from app.libs.sso import OptionalOAuth2AuthorizationCodeBearer

oauth2_scheme = OptionalOAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/authorize",
    tokenUrl=f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/token",
)


class AdminProfile(BaseModel):
    id: str = Field(...)
    mail: EmailStr = Field(...)
    displayName: str = Field(...)
    givenName: str = Field(...)
    surname: str = Field(...)
    userPrincipalName: str = Field(..., description='User Principal Name 用户主体名称')


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: Optional[str] = None


async def generate_sso_login_url() -> str:
    state = str(uuid.uuid4())
    async with RedisCacheController() as cache:
        await cache.set(str(state), 1, 60 * 5)
    auth_params = {
        "client_id": get_settings().SSO_AZURE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": get_settings().SSO_AZURE_REDIRECT_URI,
        "response_mode": "query",
        "scope": "User.Read",
        "state": state,
        "prompt": "select_account",
    }
    return f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/authorize?{urlencode(auth_params)}"


async def get_user_profile(access_token: Optional[str] = Depends(oauth2_scheme)) -> AdminProfile | None:
    if not access_token:
        return None
    try:
        async with RedisCacheController() as cache:
            if admin_profile_json := await cache.get(access_token):
                return AdminProfile.model_validate_json(admin_profile_json)
            async with httpx.AsyncClient() as client:
                response = await client.get("https://graph.microsoft.com/v1.0/me", headers={
                    "Authorization": f"Bearer {access_token}"
                })
                admin_profile = AdminProfile.model_validate(response.raise_for_status().json())
                await cache.set(access_token, admin_profile.model_dump_json(), ex=60 * 60 * 12)
                return admin_profile
    except HTTPException:
        return None
    except HTTPStatusError:
        return None
    except ValidationError:
        return None

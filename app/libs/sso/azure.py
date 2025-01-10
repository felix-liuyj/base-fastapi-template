from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import Depends
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import Field, EmailStr, BaseModel

from app.config import get_settings

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/authorize",
    tokenUrl=f"{get_settings().SSO_AZURE_BASE_URL}/oauth2/v2.0/token",
)


class AdminProfile(BaseModel):
    id: str = Field(...)
    email: EmailStr = Field(..., alias='mail')
    displayName: str = Field(...)
    givenName: str = Field(...)
    surname: str = Field(...)
    userPrincipalName: str = Field(...)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: Optional[str] = None


async def generate_sso_login_url() -> str:
    import uuid
    from app.libs.cache import RedisCacheController

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


async def get_user_profile(access_token: str = Depends(oauth2_scheme)) -> AdminProfile:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://graph.microsoft.com/v1.0/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        return AdminProfile.model_validate(response.raise_for_status().json())

from typing import Annotated

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.libs.sso.hktdc import get_user_profile, generate_sso_login_url
from app.models.account import UserProfile
from app.response import ResponseModel
from app.view_models.account import *

router = APIRouter(
    prefix='/auth', tags=['Account API'], dependencies=[]
)


@router.get(
    '/login',
    description='Login account'
)
async def login_user():
    return RedirectResponse(await generate_sso_login_url())


@router.get(
    '/callback', description='Login Auth Callback'
)
async def account_auth_callback(
        code: str = Query(..., description='Authorization code'),
        state: str = Query(..., description='Authorization state'),
        settings: Annotated[Settings, Depends(get_settings)] = None,
):
    async with AccountAuthCallbackViewModel(code, state) as response:
        # 重定向到前端，携带 Token 和用户信息
        return RedirectResponse(
            url=f"{settings.FRONTEND_DOMAIN}?accessToken={response.data.accessToken}"
        )


@router.post('/logout')
async def logout_user(
        request: Request,
        user_profile: Annotated[UserProfile, Depends(get_user_profile)]
):
    async with UserLogoutViewModel(request, user_profile) as response:
        return response


@router.get(
    '/user', response_model=ResponseModel[UserProfile], description='Get user info'
)
async def get_user_info(
        request: Request,
        user_profile: Annotated[UserProfile, Depends(get_user_profile)]
):
    # 此处的 token 会自动从 OAuth2AuthorizationCodeBearer 获取
    async with UserInfoGetViewModel(request, user_profile) as response:
        return response


@router.get('/users')
async def get_user_info_list(request: Request):
    async with UserInfoListGetViewModel(request) as response:
        return response


@router.get('/v-code')
async def send_verification_code(email: str = Query(...)):
    async with VerificationCodeSendViewModel(email) as response:
        return response

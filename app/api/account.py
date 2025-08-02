from typing import Annotated

from fastapi import Request, Query, Depends
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.libs.constants import CustomApiRouter
from app.libs.sso.azure import get_user_profile, generate_sso_login_url
from app.models.account import UserProfile
from app.response import ResponseModel
from app.response import create_response
from app.response.account import UserInfoListQueryResponseDataItem
from app.view_models.account import *

__all__ = (
    'router',
)

router = CustomApiRouter()


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
    return await create_response(
        AccountAuthCallbackViewModel, code, state, response_handler=lambda x: RedirectResponse(
            url=f"{settings.FRONTEND_DOMAIN}?accessToken={x.data.accessToken}"
        )
    )


@router.post('/logout')
async def logout_user(
        request: Request,
        user_profile: Annotated[UserProfile, Depends(get_user_profile)]
):
    return await create_response(UserLogoutViewModel, request, user_profile)


@router.get(
    '/user', response_model=ResponseModel[UserProfile], description='Get user info'
)
async def get_user_info(
        request: Request,
        user_profile: Annotated[UserProfile, Depends(get_user_profile)]
):
    # 此处的 token 会自动从 OAuth2AuthorizationCodeBearer 获取
    return await create_response(UserInfoQueryViewModel, request, user_profile)


@router.get(
    '/users', response_model=ResponseModel[list[UserInfoListQueryResponseDataItem]], description='Get user info list'
)
async def get_user_info_list(request: Request):
    return await create_response(UserInfoListQueryViewModel, request)


@router.get('/v-code')
async def send_verification_code(email: str = Query(...)):
    return await create_response(VerificationCodeSendViewModel, email)
